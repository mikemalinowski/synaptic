# Synaptic

Synaptic is a very light weight metadata system for maya. You can use it to definte 
a metadata blob for any given node in a maya scene. 

Each metadata block contains its own data storage for any json serialisable information
as well as a mechanism to tag other nodes with string look up keys.

### Example of Use

```python
import synaptic
import maya.cmds as mc

# -- Create some nodes
node_a = mc.createNode("transform")
node_b = mc.createNode("transform")

# -- Create (or get pre-existing) metadata representing
# -- node_a
meta = synaptic.get(node_a)

# -- Lets store some information in the metadata
meta.set("foobar", 123)
meta.set("is_awesome", True)

# -- Now lets show how we can retrieve that information
if meta.get("is_awesome"):
    print(meta.get("foobar"))

# -- Now lets make a link between node_a and node_b
meta.tag("rainbow", node_b)

# -- We can now retieve node_b from the metadata
# -- using the tag
print(f"Rainbow Node : {meta.find_first('rainbow')}")
```