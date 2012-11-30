
def lex(a, __cache={}):
    try:
        return __cache[a]
    except:
        i = 0
        escaped = False
        quoted = None # should be None, single or double
        x = a
        try:
            while True:
                if x[i] == '\n':
                    if quoted:
                        x = x[:i] + '\\n' + x[i+1:]
                        i += 1
                    else:
                        x = x[:i] + x[i+1:]
                        i -= 1
                elif x[i] in ("'", '"', '`') and (i == 0 or x[i-1] != '\\'):
                    if x[i] == quoted:
                        quoted = None
                    elif not quoted:
                        quoted = x[i]
                elif i > 0 and not quoted  and x[i] == ' ' and x[i-1] == ' ':
                    x = x[:i] + x[i+1:]
                    i -= 1
                i += 1
        except IndexError:
            pass
        x = x.strip()
        __cache[a] = x
        return x
