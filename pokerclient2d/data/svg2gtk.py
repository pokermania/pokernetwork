from xml.sax import make_parser, saxutils

class ContentHandler(saxutils.DefaultHandler):
    def __init__(self, string):
        self.result = ""
        parser = make_parser()
        parser.setContentHandler(self)
        parser.feed(string)
    def append(self, result):
        self.result = self.result + result
    def __str__(self):
        return self.result

class SVG2Glade(ContentHandler):
    def __init__(self, string):
        ContentHandler.__init__(self, string)
    def startElement(self, name, attrs):
        if name == "svg":
            self.append('<glade-interface><widget class="GtkWindow" id="%s"><property name="width_request">%s</property><property name="height_request">%s</property>' % (attrs['id'], attrs['width'], attrs['height']))
        elif name == "g":
            self.append('<child><widget class="GtkFixed" id="%s">' % (attrs['id']))
        elif name == "image":
            self.append('<child><widget class="GtkButton" id="%s"><property name="width_request">%s</property><property name="height_request">%s</property><property name="label"/><signal name="clicked" handler="on_%s_clicked"/></widget><packing><property name="x">%s</property><property name="y">%s</property></packing></child>' % (attrs['id'], attrs['width'], attrs['height'], attrs['id'], attrs['x'], attrs['y']))
    def endElement(self, name):
        if name == "svg":
            self.append('</widget></glade-interface>')
        elif name == "g":
            self.append('</widget></child>')

class SVG2Rc(ContentHandler):
    def __init__(self, string):
        ContentHandler.__init__(self, string)
    def startElement(self, name, attrs):
        if name == "image":
            self.append('style "%s_style" {engine "pixmap" {image {function = BOX file = "%s"}}} widget "*%s" style "%s_style"\n' % (attrs['id'], attrs['xlink:href'], attrs['id'], attrs['id']))

if __name__ == '__main__':
    import sys
    if len(sys.argv) == 2:
        if sys.argv[1] == "--glade":
            print SVG2Glade(sys.stdin.read())
        elif sys.argv[1] == "--gtkrc":
            print SVG2Rc(sys.stdin.read())
