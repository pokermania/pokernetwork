#!/usr/bin/perl

$first_time = 1;
while(<>) {
    if(/class="GtkWindow" id="(.*)_window">/) {
        print <<EOF;
<widget class="GtkWindow" id="$1_root">
EOF
    } elsif(/<widget class="GtkAlignment" id="(.*)_container">/ .. /<property name="right_padding">/) {
        if(/<widget class="GtkAlignment" id="(.*)_container">/) {
            print <<EOF;
<widget class="GtkEventBox" id="$1_window">
EOF
        } elsif(/(width|height)_request/) {
            print;
        }
    } elsif(/<property name="pixbuf">/) {
    } else {
        print;
    }
}

