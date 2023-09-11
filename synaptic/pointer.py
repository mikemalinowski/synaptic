"""
Nothing in here should be touched.
"""
import maya.api.OpenMaya as om


# --------------------------------------------------------------------------------------
def get_pointer(node_name: str) -> om.MObject:
    """
    Given the name of a node, this will return the MObject representation. This means
    we can track the node easily without having to worry about name changes.

    Args:
        node_name: Name of the node to get a pointer to

    Returns:
        MObject reference
    """
    try:
        selection_list = om.MSelectionList()
        selection_list.add(node_name)

        return selection_list.getDependNode(0)

    except RuntimeError:
        raise RuntimeError(f"Could not find node {node_name}")


# --------------------------------------------------------------------------------------
def get_name(pointer):
    """
    This will return the name of the MObject pointer

    Args:
        pointer: MObject pointer

    Returns:
        Name of the node
    """
    return om.MFnDependencyNode(pointer).name()
