import xcffib.xproto

from core.errors import NoSuchAtomWithNameError, NoSuchAtomWithIDError, NoSuchPropertyError


def get_root_window_id(conn):
    root, = conn.get_setup().roots
    root_window_id = root.root
    return root_window_id


def get_atom_id_from_name(conn, name):
    atom_id = conn.core.InternAtom(
        only_if_exists=True,
        name_len=len(name),
        name=name,
    ).reply().atom
    
    if atom_id == 0:  # No atom was found. This is normally a None enum
        raise NoSuchAtomWithNameError
    
    return atom_id


def get_atom_name_from_id(conn, atom_id):
    try:
        atom_reply = conn.core.GetAtomName(
            atom=atom_id,
        ).reply()
    except xcffib.xproto.AtomError as e:
        raise NoSuchAtomWithIDError from e

    atom_name = atom_reply.name.to_utf8()

    return atom_name


def _get_window_property_segment(conn, window_id, property_name_atom_id, offset, length):
    """ Abstracts away some of the confusing parts of the xcb GetProperty call.
    Args:
        conn: The XCB connection to the X Server which owns the given window
        window_id: The ID of the window with the given property
        property_name_atom_id: The ID of the atom with the name of the property
        offset: The number of "longs" (4 bytes) to skip before starting the segment
        length: The: maximum number of "longs" (4 bytes) after the start of the segment to pull

    Returns: XCB GetPropertyReply

    Notes:
        On the type argument:
            Seeing as the type of a variable is effectively an attribute of that variable, it seems unusual that one
                would need to know the type of a variable in order to "get" it, especially given that:
                    1. The X Server (to my understanding) just treats the type field as another arbitrary string.
                    2. The "actual" type is returned
                What I gather from the manual's documentation on this function [1] is that supplying an incorrect type
                can be used to get the actual type as well as the format and full length, without getting the value.
                Beyond that, I cannot find any compelling reason to find and pass the actual type rather than the "Any"
                wildcard (in which case the type is returned anyway).
    
    Links:
        [1]: https://www.x.org/docs/X11/xlib.pdf
    """
    property_segment = conn.core.GetProperty(
        delete=False,  # Apparently this getter is also a deleter
        window=window_id,
        property=property_name_atom_id,
        type=xcffib.xproto.GetPropertyType.Any,  # See Notes above
        long_offset=offset,
        long_length=length,
    ).reply()

    return property_segment


def get_window_property(conn, window_id, property_name_atom_id, size_hint=100):
    def segment_getter(offset, length):
        return _get_window_property_segment(
            conn=conn,
            window_id=window_id,
            property_name_atom_id=property_name_atom_id,
            offset=offset,
            length=length,
        )

    property_reply = segment_getter(
        offset=0,
        length=size_hint,
    )

    buffer = property_reply.value.raw

    if property_reply.format == 0:  # Property doesn't exist
        raise NoSuchPropertyError

    if property_reply.bytes_after > 0:  # In case size_hint < actual size
        rest = segment_getter(
            offset=len(property_reply.value)//4+1,
            length=property_reply.bytes_after//4,
        )
        buffer += rest.value.raw

    return buffer, property_reply.type, property_reply.format
