"""
Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""
import json
import typing
import maya.cmds as mc

from . import pointer


# --------------------------------------------------------------------------------------
class Metadata:
    """
    The metadata class creates and wraps around a network node which contains various
    _Attributes to store both information and links to other objects.

    Information Storage:

        You can store and retrieve information from the metadata node using
        the Metadata.get(label) and Metadata.set(label, value)

        Internally these are stored in persistentData and transientData as a json
        serialised string. Typically, you should not access these _Attributes directly,
        instead you should use the .get and .set methods shown below. The reasoning for
        this is that the .set will only ever set data in the transientData attribute
        when the node is referenced. This ensures that any data that is set when
        referenced will not prevent any changes coming through from the base file. This
        is because when you call .get it will actually take the persistentData and then
        update it with the transientData to get the final result.

    Tagging:

        The Metadata class allows you to tag other nodes within the scene using a
        label, which makes retrieving them easier.

        For instance, you can call Metadata.tag("foobar", "some_node"). This will
        create a message link between the network node and the node named "some_node".

        This is useful because you can now find that node using Metadata.find("foobar")
        instead of referencing the node by name. This makes it particularly good for
        making parts of your scene name agnostic.
    """
    identifier = ""
    version = 1.0

    _NODE_NAME = "SYNAPTIC_METANODE"
    _TAG_PREFIX = "usertag"

    # ----------------------------------------------------------------------------------
    def __init__(self, node: str):

        # -- Store a pointer to the object. This way we can always retrieve
        # -- it regardless of name changes
        self._host_pointer = pointer.get_pointer(node)

        # -- Look for the metanode which represents this host, and store
        # -- a pointer to that also
        self._meta_pointer = pointer.get_pointer(
            self.get_metanode(
                node,
            ),
        )

    # ----------------------------------------------------------------------------------
    @classmethod
    def get_metanode(cls, host: str) -> str:
        """
        This function allows for the metanode name to be returned for the given
        host node.

        Args:
            host (str): The name of the node you want to query

        Returns:
            str: The name of the metanode (network node)
        """
        # -- We want to look explicitly for the receiving plug data, as we
        # -- only want to find the first one that has a host connection.
        all_plugs = mc.listConnections(
            f"{host}.message",
            source=False,
            destination=True,
            connections=True,
            plugs=True,
        )
        if not all_plugs:
            return ""

        # -- The listConnections call gives us a flat array, but its actually
        # -- a one dimensional array of double data. So iterate over it in
        # -- twos
        for target_attr in all_plugs[1::2]:
            if target_attr.endswith('.host'):

                # -- We have a valid connection - so extract the metanode
                # -- name from it
                return target_attr.rsplit('.', 1)[0]

        return ""

    # ----------------------------------------------------------------------------------
    @classmethod
    def create(cls, host_node: str) -> "Metadata":
        """
        This will create a metanode to represeent the given host node

        Args:
            host_node: (str) The name of the node you want to create a metanode
                for 

        Returns:
            Metadata: An instance of this class representing the metadata node
                that was just created.
        """
        
        # -- Create the network node
        meta_node = mc.createNode("network", name=cls._NODE_NAME + '#', skipSelect=True)
        
        # -- Add the attribute we use to ensure its a synapitic metanode
        mc.addAttr(
            meta_node,
            shortName=_Attributes.SYNAPTIC,
            at="bool",
        )

        # -- This attribute is what ties the meta network node to the node
        # -- we want to store metadata for
        mc.addAttr(
            meta_node,
            shortName=_Attributes.HOST,
            at="message",
        )
        mc.connectAttr(
            f"{host_node}.message",
            f"{meta_node}.{_Attributes.HOST}"
        )

        # -- This attribute is used to store data which cannot be changed
        # -- during a reference
        mc.addAttr(
            meta_node,
            shortName=_Attributes.PERSISTENT_DATA,
            dt="string",
        )
        mc.setAttr(
            f"{meta_node}.{_Attributes.PERSISTENT_DATA}",
            "{}",
            type="string",
        )

        # -- This attribute is used to store transient data - typically data
        # -- specific to a reference
        mc.addAttr(
            meta_node,
            shortName=_Attributes.TRANSIENT_DATA,
            dt="string",
        )
        mc.setAttr(
            f"{meta_node}.{_Attributes.TRANSIENT_DATA}",
            "{}",
            type="string",
        )

        return Metadata(host_node)

    # ----------------------------------------------------------------------------------
    def set(self, label: str, value: typing.Any) -> None:
        """
        This allows you to store a piece of information in the metadata as a key
        value pair. Note that the value (and the key) must be json serialisable.
        
        Args:
            label: A label to store the data against. It is this label you can
                later use to retrieve the value
                
            value: The value you want to store in the metadata.  

        Returns:
            None
        """
        # -- If we're referenced then we apply the data into the transient
        # -- attribute. This is to ensure we NEVER alter the perisistent data
        # -- in a reference. That allows for the data to always be updated in teh
        # -- source file.
        meta_name = pointer.get_name(self._meta_pointer)

        is_referenced = mc.referenceQuery(
            meta_name,
            isNodeReferenced=True,
        )

        if is_referenced:
            attr = _Attributes.TRANSIENT_DATA

        else:
            attr = _Attributes.PERSISTENT_DATA

        # -- Attempt to get the stored data as a dictionary
        try:
            current_data = json.loads(
                mc.getAttr(
                    f"{meta_name}.{attr}",
                ),
            )

        except json.JSONDecodeError:
            current_data = dict()

        # -- Add in our value
        current_data[label] = value

        # -- Apply the data back onto the attribute
        mc.setAttr(
            f"{meta_name}.{attr}",
            json.dumps(current_data),
            type="string",
        )

    # ----------------------------------------------------------------------------------
    def get(self, label: str) -> typing.Any:
        """
        This will retrieve the value stored against the given label. If the label
        is not found within the metadata node then None will be returned.
        Args:
            label: 

        Returns:

        """
        # -- Get the name of the meta node
        meta_name = pointer.get_name(self._meta_pointer)

        # -- Get the data from the persistent attribute
        try:
            all_data = json.loads(
                mc.getAttr(
                    f"{meta_name}.{_Attributes.PERSISTENT_DATA}",
                ),
            )
        except json.JSONDecodeError:
            all_data = dict()

        # -- Now compound that with the data from the transient. Note that we
        # -- stamp the persistent data with the transient, because we allow
        # -- transient settings to overlay on top of the persistent data
        try:
            all_data.update(
                mc.getAttr(
                    f"{meta_name}.{_Attributes.TRANSIENT_DATA}",
                ),
            )

        except (json.JSONDecodeError, ValueError):
            pass

        # -- Return the value with the given label. If the label is not
        # -- present we simply return None
        return all_data.get(label, None)

    # ----------------------------------------------------------------------------------
    def tag(self, tag_name: str, target: str) -> None:
        """
        This allows you to tag another node in the scene graph. This allows you to 
        retrieve that node using a tag name rather than the actual objects name.
        
        This is useful for many situations. An example might be to tag all the deformers
        which make up part of a rig. By using tags to define object relative look up's 
        you're no longer relying purely on the names.
        
        Args:
            tag_name:  The name to store the tag as. This can be thought of as a 
                dictionary key.
                
            target: The name of the node you want to store a connection tag to
            
        Returns:
            None
        """
        # -- Pre-append the tag name without tagging prefix
        tag_name = self._TAG_PREFIX + tag_name
        meta_name = pointer.get_name(self._meta_pointer)

        # -- Store the node + attribute name to avoid reformatting each time
        attribute_fullpath = f"{meta_name}.{tag_name}"

        # -- Add the attribute
        if not mc.objExists(attribute_fullpath):
            mc.addAttr(
                meta_name,
                shortName=tag_name,
                at="message",
                multi=True,
            )

        try:
            next_index = mc.getAttr(
                attribute_fullpath,
                multiIndices=True,
            )[-1] + 1

        except (TypeError, IndexError):
            next_index = 0

        mc.connectAttr(
            f"{target}.message",
            f"{attribute_fullpath}[{next_index}]",
            force=True,
        )

    # ----------------------------------------------------------------------------------
    def untag(self, tag_name: str, target: str):
        """
        THis will remove a tag from the metadata. If that tag does not exist then 
        no action will occur.
        
        Args:
            tag_name: Name of tag to remove
            target: Name of node to remove tag from

        Returns:
            None
        """
        # -- Pre-append the tag name without tagging prefix
        tag_name = self._TAG_PREFIX + tag_name

        # -- Get the name of the meta node from the pointer
        meta_name = pointer.get_name(self._meta_pointer)

        # -- Store the node + attribute name to avoid reformatting each time
        attribute_fullpath = f"{meta_name}.{tag_name}"

        # -- Add the attribute does not exist, we have no nodes
        # -- to collate
        if not mc.objExists(attribute_fullpath):
            return

        connection_info = mc.listConnections(
            attribute_fullpath,
            source=True,
            destination=False,
            connections=True,
            plugs=True,
        )

        if not connection_info:
            return

        for idx in range(0, len(connection_info), 2):
            meta_attr = connection_info[idx]
            target_attr = connection_info[idx + 1]

            if target_attr.rsplit(".", 1)[0] == target:
                mc.disconnectAttr(
                    target_attr,
                    meta_attr,
                )

    # ----------------------------------------------------------------------------------
    def find(self, tag_name: str) -> typing.List[str]:
        """
        This will find all the nodes tagged to this metadata with the given tag name
        
        Args:
            tag_name: (str) The name of the tag to look up

        Returns:
            list(str): List of node names which were tagged 
        """
        # -- Pre-append the tag name with out tagging prefix
        tag_name = self._TAG_PREFIX + tag_name

        # -- Get the name of the meta node from the pointer
        meta_name = pointer.get_name(self._meta_pointer)

        # -- Store the node + attribute name to avoid reformatting each time
        attribute_fullpath = f"{meta_name}.{tag_name}"

        # -- Add the attribute does not exist, we have no nodes
        # -- to collate
        if not mc.objExists(attribute_fullpath):
            return list()

        return list(
            set(
                mc.listConnections(
                    attribute_fullpath,
                    source=True,
                    destination=False,
                ) or list(),
            ),
        )

    # ----------------------------------------------------------------------------------
    def find_first(self, tag_name):
        """
        This will find the first node tagged to this metadata with the given tag name

        Args:
            tag_name: (str) The name of the tag to look up

        Returns:
            str: The first node name with a match 
        """
        results = self.find(tag_name)

        if results:
            return results[0]

        return None

    # ----------------------------------------------------------------------------------
    def node(self) -> str:
        """
        This will return the node name of the actual metadata node
        
        Returns:
            Node name of the metadata (network) node
        """
        return pointer.get_name(self._meta_pointer)

    # ----------------------------------------------------------------------------------
    def host(self):
        """
        This will return the node name of the node this metadata represents
        
        Returns:
            Node name of the node which the metadata represents
        """
        return pointer.get_name(self._host_pointer)


# --------------------------------------------------------------------------------------
class _Attributes:
    """
    This is a constants look up for the attributes stored on the metadata
    """
    SYNAPTIC = "SYNAPTIC"
    HOST = "host"
    PERSISTENT_DATA = "persistentData"
    TRANSIENT_DATA = "transientData"


# --------------------------------------------------------------------------------------
def has_meta(node: str) -> bool:
    """
    This is a convenience function which returns True or False as to whether the
    given node has a metadata node connected to it

    Args:
        node: Name of node to query

    Returns:
        bool: True if the  given node has metadata
    """
    return True if Metadata.get_metanode(node) else False


# --------------------------------------------------------------------------------------
def get(node: str) -> Metadata:
    """
    This is a convenience function for returning a Metadata class instance for the
    given node providing the node has metadata. If it does not then None will be
    returned.

    Args:
        node: Name of node to attmept to get the Metadata class instance for

    Returns:
        Metadata
    """
    if has_meta(node):
        return Metadata(node)

    return None


# --------------------------------------------------------------------------------------
def create(node: str) -> Metadata:
    """
    This will create a metadatanode for the given node providing it does not already
    have one.

    Args:
        node: Name of the node to create the metadata for

    Returns:
        Metadata instance
    """
    # -- If this node already has metadata, we dont want to create it again, so
    # -- just return what is there
    pre_meta = Metadata.get_metanode(node)

    if pre_meta:
        return get(pre_meta)

    # -- Create it
    return Metadata.create(node)
