from time import strftime, strptime
import urllib
import pycurl
import libxml2
import re
import os

def check_digits_only(map, name):
    if map.has_key(name) and not re.match('^[0-9]+$', map[name]):
        raise UserWarning, name + " is not made of digits only" 

def check_alnum_only(map, name):
    if map.has_key(name) and not re.match('^\w+$', map[name]):
        raise UserWarning, name + " is not made of alphanumerical characters only" 

def check_amount(map, name):
    if map.has_key(name) and not re.match('^[0-9]*(?:\.[0-9]{1,2})?$', map[name]):
        raise UserWarning, name + " is not made of digits and two digit decimal only" 

def check_words_and_space_only(map, name):
    if map.has_key(name) and not re.match('^[\w\s]*$', map[name]):
        raise UserWarning, name + " must be all alphanumeric and space"
    
def check_length(map, name, min, max):
    if map.has_key(name) and len(map[name]) not in range(min,max+1):
        raise UserWarning, name + " length must be between " + str(min) + " and " + str(max) + " characters long" 

def check_min_length(map, name, min):
    if map.has_key(name) and len(map[name]) < min:
        raise UserWarning, name + " length must be at least " + str(min) + " characters long" 

def check_max_length(map, name, max):
    if map.has_key(name) and len(map[name]) > max:
        raise UserWarning, name + " length must be at most " + str(max) + " characters long" 

def check_exact_length(map, name, length):
    if map.has_key(name) and len(map[name]) != length:
        raise UserWarning, name + " length must be exactly " + str(length) + " characters long" 

def check_is_in(map, name, values):
    if map.has_key(name) and map[name] not in values:
        raise UserWarning, name + " is not among the supported values (" + str(values) + ")" 
        
def check_mandatory_fields(parameters, fields):
    missing_fields = []
    for key in fields:
        if not parameters.has_key(key) or not parameters[key]:
            missing_fields.append(key)
    if missing_fields:
        raise UserWarning, "Missing mandatory field(s) " + str(missing_fields) + " in request " + str(parameters)
    
class Neteller:
    """
    """
    CURRENCIES = ( 'USD', 'EUR', 'GBP', 'CAD' )
    URL = 'https://www.neteller.com/'

    def __init__(self, *args, **kwargs):
        self.parameters = kwargs
        if not hasattr(self, 'CURRENCIES'): self.CURRENCIES = Neteller.CURRENCIES
        self.verbose = kwargs.get('verbose', 0)

    def request_validate(self, parameters):
        check_mandatory_fields(parameters, self.REQUEST_FIELDS_MANDATORY)
        
        check_amount(parameters, 'amount')
        
        check_is_in(parameters, 'currency', self.CURRENCIES)

        check_length(parameters, 'merchant_id', 2, 4)

        check_exact_length(parameters, 'merchant_key', 6)

        check_alnum_only(parameters, 'merch_pass')

        check_digits_only(parameters, 'net_account')
        check_exact_length(parameters, 'net_account', 12)

        check_digits_only(parameters, 'secure_id')
        check_exact_length(parameters, 'secure_id', 6)

        check_max_length(parameters, 'merch_account', 50)
        check_words_and_space_only(parameters, 'merch_account')

        check_is_in(parameters, 'Test', ('0', '1'))

        check_is_in(parameters, 'Error', self.ERRORS)
        
    def request(self, *args, **kwargs):
        parameters = self.parameters.copy()

        for key in self.REQUEST_FIELDS_MANDATORY + self.REQUEST_FIELDS_OPTIONAL:
            if kwargs.has_key(key):
                parameters[key] = kwargs[key]

        self.request_validate(parameters)

        class Collect:
            def __init__(self):
                self.contents = ''

            def body_callback(self, buf):
                self.contents = self.contents + buf

        collect = Collect()
        url = self.URL + self.FORM
        curl = pycurl.Curl()
        if os.name != "posix":
            curl.setopt(curl.SSL_VERIFYPEER, False)
        curl.setopt(curl.URL, self.URL + self.FORM)
        curl.setopt(curl.WRITEFUNCTION, collect.body_callback)
        curl.setopt(curl.POSTFIELDS, urllib.urlencode(parameters))
        curl.setopt(curl.VERBOSE, self.verbose)
        curl.perform()
        curl.close()
        # remove extra space at the beginning of the XML document
        buffer = collect.contents[len(re.match(r'(\s*)', collect.contents).group(1)):]
        reader = libxml2.readerForMemory(buffer, len(buffer), url, 'iso8859-1', 0)
        if reader.Read() != 1:
            raise UserWarning, "Unable to read first element from " + buffer

        if reader.NodeType() != libxml2.XML_READER_TYPE_ELEMENT or reader.Name() != self.ANSWER_ELEMENT:
            raise UserWarning, "Top level element must be <" + self.ANSWER_ELEMENT + "> " + buffer

        if reader.AttributeCount() != 1 or reader.MoveToAttributeNo(0) != 1:
            raise UserWarning, "<" + self.ANSWER_ELEMENT + "> must have exactly one attribute" + buffer

        if reader.Name() != 'version':
            raise UserWarning, "<" + self.ANSWER_ELEMENT + "> must have version attribute " + buffer
            
        if reader.Value() != self.VERSION:
            raise UserWarning, "<" + self.ANSWER_ELEMENT + "> version is " + reader.Value() + " but " + self.VERSION + " was expected" + buffer

        if reader.Read() != 1:
            raise UserWarning, "Unexpected end of file after <netwith> element: " + buffer

        answer = {}
        ret = 1
        while ret == 1:
            if self.verbose > 1: print "Reader: %s %s %d" % (reader.NodeType(),reader.Name(),reader.Depth())
            if reader.NodeType() == libxml2.XML_READER_TYPE_ELEMENT:
                name = reader.Name()
                if reader.Read() != 1:
                    raise UserWarning, "Unexpected end of file after " + name + " element: " + buffer
                if reader.NodeType() == libxml2.XML_READER_TYPE_TEXT:
                    answer[name] = reader.Value()
                else:
                    raise UserWarning, "Unexpected end of node of type " + str(reader.NodeType()) + " after " + name + " element: " + buffer
            ret = reader.Read()

        if self.verbose:
            print "Answer: " + str(answer)
            print "XML:\n---\n%s\n---" % buffer

        #
        # Readable errors
        #
        if answer.has_key('error'):
            if answer['error'] == 'none':
                del answer['error']
            else:
                error = "<unknown>"
                if not self.ERRORS.has_key(answer['error']):
                    raise UserWarning, "Unknown error " + answer['error'] + " from " + str(answer) 
                answer['error'] = ( answer['error'], self.ERRORS[answer['error']] )
        #
        # Convert time from string to number
        #
        if answer.has_key('time'):
            pattern = "^{ts '(.*)'}"
            match = re.match(pattern, answer['time'])
            if match:
                answer['time'] = strftime("%s", strptime(match.group(1), '%Y-%m-%d %H:%M:%S'))
            else:
                raise UserWarning, "answer time field " + answer['time'] + " does not match " + pattern
        
        return answer

class NetellerCashIn(Neteller):
    """
    NETeller DIRECT v4.0 (page 4)
    implementation
    """
    ERRORS = {
        '1001': 'One or more of the variables that has been listed as required has not been sent or has not been received properly by the NETeller Direct API.',
        '1002': 'There is a problem with the length of the net_account or secure_id variables.',
        
        '1003': 'One of the variables, net_account, secure_id, merchant_id or amount, are not in numeric format.',
        '1004': 'No Merchant was found for the Merchant ID that was specified.',
     
        '1005': 'The amount that was specified is above or below the specified limits.',
     
        '1006': 'There is a problem with your Merchant Account. Please contact NETeller Merchant Services.',
     
        '1007': 'No client has been found for the specified net_account variable.',
        '1008': 'The specifed secure_id does not match to the net_account variable that was specified.',
        '1009': 'The specified member NETeller Account has been temporarily suspended, please have them contact NETeller Customer Service.',
        '1010': 'The amount specified is above the NETeller member\'s available balance.',

        '1011': 'The specified member is currently not permitted to use their bank account. Please have them contact NETeller Customer Service. You will only receive this error when using the Direct AcceptTM option.',
        '1012': 'There is a problem with the bank account number the NETeller member specified and it will not be able to be used at this time. You will only receive this error when using the Direct AcceptTM option.',
        
        '1013': 'The amount the member has specified is above their Direct Accept limits. Please have the member check their NETeller Account to see what their limits are. You will only receive this error when using the Direct AcceptTM option.',
        
        '1014': 'Member account error -- transaction will not be approved. Have the member contact NETeller Customer Service. You will only receive this error when using the Direct AcceptTM option.',
        '1015': 'Invalid currency. Your Merchant Account or sub-accounts do not support this currency.', 
        '1016': 'Unexpected error. Transaction Failed.',                                                 
        '1017': 'Merchant is not enabled to have live Transfers, only test transactions are allowed.',   
        '1018': 'Merchant account error.',                                                               
        '1019': 'Currency and transaction request not currently supported.',                             
        '1020': 'Supplied net_account invalid while submitting a test transaction.',
        '1023': 'Transaction not completed. You must sign in to your NETELLER account and accept the Terms and Conditions.',
        }

    REQUEST_FIELDS_MANDATORY = (
        'amount',
        'merchant_id',
        'net_account',
        'secure_id',
        'merch_transid',
        'currency'
        )

    REQUEST_FIELDS_OPTIONAL = (
        'bank_acct_num',
        'merch_account',
        'custom_1',
        'custom_2',
        'custom_3',
        'Email',
        'Test',
        'Error'
        )

    def __init__(self, *args, **kwargs):
        Neteller.__init__(self, *args, **kwargs)
        self.FORM = 'gateway/netdirectv4.cfm'
        self.VERSION = '4.0'
        self.ANSWER_ELEMENT = 'netdirect'
        self.REQUEST_FIELDS_MANDATORY = NetellerCashIn.REQUEST_FIELDS_MANDATORY
        self.REQUEST_FIELDS_OPTIONAL = NetellerCashIn.REQUEST_FIELDS_OPTIONAL
        self.ANSWER_FIELDS = ( 'approval', 'amount', 'trans_id', 'error', 'fee', 'time', 'firstname', 'lastname', 'email', 'custom_1', 'custom_2', 'custom_3', 'dafee', 'client_currency', 'client_amount', 'merchant_currency', 'merchant_amount', 'fxrate' )
        self.ERRORS = NetellerCashIn.ERRORS

class NetellerCashOut(Neteller):
    """
    NETeller Direct Automated Payouts v3.0
    implementation
    """
    ERRORS = {
        '1001': 'No Merchant ID specified.',
        '1002': 'No NETeller Merchant Password specified.',
        '1003': 'No NETeller Merchant Key specified.',
        '1004': 'No NETeller Client Account ID specified.',
        '1005': 'No Amount specified.',
        '1006': 'Invalid Merchant Key specified.',
        '1007': 'Invalid Merchant ID specified.',
        '1008': 'No Merchant found for that Merchant ID.',
        '1009': 'Password is incorrect for that Merchant ID.',
        '1010': 'Merchant Key is incorrect for that Merchant ID.',
        '1011': 'No Client found for that NETeller Account ID.',
        '1012': 'NETeller Account ID for client specified is invalid.',
        '1013': 'Amount specified is too high.',
        '1014': 'Amount specified is too low.',
        '1015': 'Amount specified is invalid.',
        '1016': 'Merchant does not have enough funds available for that payout.',
        '1017': 'Your merchant account is not setup to accept the requested currency.',
        '1018': 'Unexpected error. Transaction failed.',
        '1019': 'Merchant account is not enabled for live multiple currency transactions.',
        '1020': 'There is a problem in your merchant account configuration contact NETeller support.',
        '1021': 'The client account used is a test account and no live transactions are permitted.',
        '1022': 'Requested currency is not supported by our systems.',
        }

    def __init__(self, *args, **kwargs):
        Neteller.__init__(self, *args, **kwargs)
        self.FORM = 'gateway/withtellerv3.cfm'
        self.VERSION = '3.0'
        self.ANSWER_ELEMENT = 'netwith'
        self.CURRENCIES = ( 'USD', 'EUR', 'GBP' )
        self.REQUEST_FIELDS_MANDATORY = ( 'amount', 'currency', 'merchant_id', 'merch_pass', 'merch_key', 'net_account' )
        self.REQUEST_FIELDS_OPTIONAL = ('custom_1', 'custom_2', 'custom_3', 'merch_account', 'Test', 'Error')
        self.ANSWER_FIELDS = ( 'approval', 'amount', 'trans_id', 'custom_1', 'custom_2', 'custom_3', 'error', 'fee', 'time', 'firstname', 'lastname', 'sourcecurrency', 'sourceamount', 'destinationcurrency', 'destinationamount', 'fxrate' )
        self.ERRORS = NetellerCashOut.ERRORS

class NetellerCheck(Neteller):
    """
    NETeller DIRECT v4.0 (Checking on Transaction Status, page 10)
    implementation
    """
    ERRORS = {
        '1001': 'Merchant ID or unique Transaction ID were not received correctly.',
        '1002': 'A successful transaction was not found for that unique ID.',
        }

    def __init__(self, *args, **kwargs):
        self.FORM = 'gateway/netcheck4.cfm'
        self.VERSION = '4.0'
        self.ANSWER_ELEMENT = 'netdirect'
        self.REQUEST_FIELDS_MANDATORY = ( 'merchant_id', 'merch_transid' )
        self.REQUEST_FIELDS_OPTIONAL = ()
        self.ANSWER_FIELDS = ( 'approval', 'amount', 'trans_id', 'error', 'fee', 'time', 'firstname', 'lastname', 'email', 'dafee', 'client_currency', 'client_amount', 'merchant_currency', 'merchant_amount' )
        self.ERRORS = NetellerCheck.ERRORS
        Neteller.__init__(self, *args, **kwargs)
        
if __name__ == "__main__":

    import ConfigParser
    import getopt, sys
    from types import *
    
    def usage(message):
        print message
        print """
neteller.py [--config=<path>] (in|out|check) 
"""
        sys.exit(1)

    def dry_run_patch(kwargs, command, verbose):
        kwargs['Test'] = '1'
        if command == "in":
            #    AccountID       SecureId    Currency
            cashin = (
                ('458415554241', '896365', 'USD'),
                ('451015522412', '568492', 'GBP'),
                ('456115522530', '362626', 'EUR'),
                ('455715767192', '283419', 'CAD'),
                )
            input = ( kwargs['net_account'], kwargs['secure_id'], kwargs['currency'] )
            if input not in cashin:
                if verbose:
                    print "Invalid test input for command '" + command + "' : " + str(input) + " changed with " + str(cashin[0])
                ( kwargs['net_account'], kwargs['secure_id'], kwargs['currency'] ) = cashin[0]
        
        elif command == "out":
            cashout = (
                ('458415554241', 'USD'),
                ('451015522412', 'GBP'),
                ('456115522530', 'EUR'),
                )
            input = ( kwargs['net_account'], kwargs['currency'] )
            if input not in cashout:
                if verbose:
                    print "Invalid test input for command '" + command + "' : " + str(input) + " changed with " + str(cashout[0])
                ( kwargs['net_account'], kwargs['currency'] ) = cashout[0]

        
    def main():
        try:
            opts, args = getopt.getopt(sys.argv[1:], "hcvdop", ["help", "config=", "verbose", "dry-run", "option=", "php" ])
        except getopt.GetoptError:
            usage()
            sys.exit(2)
        config_path = "neteller.cfg"
        verbose = 0
        dry_run = False
        kwargs = {}
        php = False
        for o, a in opts:
            if o in ("-h", "--help"):
                usage()
                sys.exit(0)
            if o in ("-c", "--config"):
                config_path = a
            if o in ("-d", "--dry-run"):
                dry_run = True
            if o in ("-p", "--php"):
                php = True
            if o in ("-o", "--option"):
                for pair in a.split("&"):
                    ( key, value ) = pair.split("=")
                    kwargs[key] = value
            if o in ("-v", "--verbose"):
                verbose += 1

        config = ConfigParser.SafeConfigParser()
        config.read(config_path)

        if len(args) < 1: usage("no argument provided")
        command = args.pop(0)

        kwargs['verbose'] = verbose
        if dry_run: dry_run_patch(kwargs, command, verbose)

        if verbose: print "kwargs " + str(kwargs)
        
        kwargs['merchant_id'] = config.get('merchant', 'merchant_id')
        kwargs['merch_pass'] = config.get('merchant', 'merch_pass')
        kwargs['merch_key'] = config.get('merchant', 'merch_key')

        result = {}
        if command == "in":
            o = NetellerCashIn(**kwargs)
        elif command == "out":
            o = NetellerCashOut(**kwargs)
        elif command == "check":
            o = NetellerCheck(**kwargs)
        else:
            usage("unknown command " + command)

        try:
            result = o.request()
        except UserWarning, error:
            if php:
                string = str(error)
                print "array('error', '" + string.replace("'", "\\'") + "');";
                sys.exit(0)
            raise
        
        if php:
            buffer = "array("
            for (key, value) in result.iteritems():
                if value == None:
                    continue
                if len(key) > len("custom") and key[:len("custom")] == "custom" and value == "none":
                    continue
                buffer += "'%s' => " % key
                if type(value) is ListType or type(value) is TupleType:
                    buffer += "array" + str(value)
                else:
                    buffer += "'%s'" % value
                buffer += ", "
            buffer += ");"
            print buffer
        else:
            print result
        
        sys.exit(0)

    main()
