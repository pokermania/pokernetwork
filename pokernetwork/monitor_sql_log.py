def handle_event(service, packet):
    '''monitor handler, called by the pokerserver'''
    sql = "INSERT INTO monitor (event, param1, param2, param3 ) VALUES (%d, %d, %d, %d)" % (
        packet.event,
        packet.param1,
        packet.param2,
        packet.param3
    )
    if service.verbose > 3:
        service.message(sql)
    service.db.db.query(sql)
