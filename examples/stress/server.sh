ulimit -n 10240
yes | mysqladmin drop pokernetworktest
nohup python -u /usr/sbin/pokerserver poker.server.xml >server.out 2>&1 &
tail -f server.out
