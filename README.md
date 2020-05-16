# What is it
Bodged-Together `xprop`-like object oriented mini-library for reading X11 window properties. Running main.py will currently print a list of the names of all the open windows (assuming the window manager supports EWMH)

# TODO (if I ever get to it):
- load format/dformat from https://gitlab.freedesktop.org/xorg/app/xprop/-/blob/master/xprop.c
- decouple from struct/array (find alternative to struct codes for unpacking)
- maybe (very unlikely) add ability to set properties (property encoder)