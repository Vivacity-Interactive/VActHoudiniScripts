import json, os

node = hou.pwd()
geo = node.geometry()

notes = node.parm("notes").eval()
dir = node.parm("dir").eval()
name = node.parm("name").eval()
module = node.parm("module").eval()
asset = node.parm("asset").eval()

scale_correct = node.parm("scalecorrect").eval()

p_force = node.parm("force")
p_format = node.parm("format")
p_axis = node.parm("axis")

axis = p_axis.menuItems()[p_axis.eval()]
format = p_format.menuItems()[p_format.eval()]
force = p_force.menuItems()[p_force.eval()]

b_hash = node.parm("bhash")
b_module = geo.findPointAttrib("module") is not None
b_asset = geo.findPointAttrib("asset") is not None
b_type = geo.findPointAttrib("type") is not None
b_parent = geo.findPointAttrib("parent") is not None

def vact_hash(a, b, f=0, szf=1): 
    return ((a * 73856093 ^ b * 19349663) << szf) | int(f)

def vact_axis_unity(p, q, s, scale=1):
    # RH Yu Xf -> LH Yu Zf
    q = hou.Quaternion(q[0],q[1],q[2],q[3]).conjugate()
    p = hou.Vector3(p) * scale
    return ((p[2], p[1], p[0]), (q[2], q[1], q[0], q[3]), (s[2], s[1], s[0]))
    
def vact_axis_babylonjs(p, q, s, scale=1):
    # RH Yu Xf -> LH Yu Zf
    return vact_axis_unity(p, q, s, scale) 

def vact_axis_treejs(p, q, s, scale=1):
    # RH Yu Xf -> RH Yu Zf
    p = hou.Vector3(p) * scale
    return ((p[2], p[1], p[0]), (q[2], q[1], q[0], q[3]), (s[2], s[1], s[0]))
    
def vact_axis_unrealengine(p, q, s, scale=1):
    # RH Yu Xf -> LH Zu Xf
    #rotate x axis 90d
    #flip on the yaxis
    q = hou.Quaternion(q).conjugate()
    p = hou.Vector3(p) * scale
    return ((p[0], p[2], p[1]), (q[0], q[2], q[1], q[3]), (s[0], s[2], s[1]))

def vact_axis_blender(p, q, s, scale=1):
    # RH Yu Xf -> RH Zu nYf
    q = hou.Quaternion(q[0],q[1],q[2],q[3]).conjugate()
    p = hou.Vector3(p) * scale
    return ((-p[0], p[2], p[1]), (q[0], q[2], q[1], q[3]), (s[0], s[2], s[1]))
    
def vact_axis_houdini(p, q, s, scale=1):
    # RH Yu Xf -> RH Yu Xf
    return (tuple(hou.Vector3(p) * scale), tuple(q), tuple(s))
    
def vact_axis(axis):
    if axis in {'Unity', 'BabylonJs'}: return vact_axis_unity
    elif axis in {'TreeJS'}: return vact_axis_treejs
    elif axis in {'UnrealEngine'}: return vact_axis_unrealengine
    elif axis in {'Blender'}: return vact_axis_blender
    else: return vact_axis_houdini
    
    
class VActOIC:
    class Property:
        def __init__(self):
            self.name = "_Unknown"
            self.type = "_Unknown"
            self.value = None
        
        def json(self):
            _fval = str if self.type not in {'String'} else json.dumps
            _value = f"({','.join(map(_fval, self.value))})" if isinstance(self.value, tuple) else _fval(self.value)
            return f"{self.name}:{_value}"
     
    class Instance:
        def __init__(self):
            self.id = -1
            self.object = -1
            self.parent = -1
            self.meta = -1
            self.transform = None

        def json(self):
            _transform = ','.join((f"({','.join(map(str, x))})" for x in self.transform))
            return f"({self.id},{self.object},{self.parent},{self.meta},({_transform}))"
            
    class Object:
        def __init__(self):
            self.id = -1
            self.type = "_Unknown"
            self.asset = ""
            self.meta = -1

        def json(self):
            return f"{{Type:{self.type},Asset:{json.dumps(self.asset)},Meta:{self.meta}}}"

    class Meta:
        def __init__(self):
            self.id = -1
            self.entries = []

        def add_entry(self, entry):
            self.entries.append(entry)
            return len(self.entries)
        
        def has(self):
            return len(self.entries) > 0
        
        def json(self):
            return f"[{','.join((x.json() for x in self.entries))}]"
            
    class MetaEntry:
        def __init__(self):
            self.asset = "_Unknown"
            self.properties = []
        
        def add_property(self, property):
            self.properties.append(property)
            return len(self.properties)
        
        def has(self):
            return len(self.properties) > 0
        
        def json(self):
            _properties = f"{{{','.join((x.json() for x in self.properties))}}}"
            return f"{{Asset:{json.dumps(self.asset)},Properties:{_properties}}}"
            
    def __init__(self, name="_Nameless" ):
        self.type = "OIC"
        self.version = "v2"
        self.axis = "_Unknown"
        self.notes = ""
        self.title = name
        self.name = name
        self.objects = []
        self.instances = []
        self.metas = []
    
    def add_instance(self, item):
        item.id = len(self.instances)
        self.instances.append(item)
        return item.id
    
    def add_object(self, item):
        item.id = len(self.objects)
        self.objects.append(item)
        return item.id
    
    def add_meta(self, item):
        item.id = len(self.metas)
        self.metas.append(item)
        return item.id
    
    def optimize(self):
        pass

    def json(self):
        _objects = f"[{','.join((x.json() for x in self.objects))}]"
        _instances = f"[{','.join((x.json() for x in self.instances))}]"
        _metas = f"[{','.join((x.json() for x in self.metas))}]"
        return f"{{Type:{self.type},Version:{self.version},Axis:{self.axis},Notes:{json.dumps(self.notes)},Title:{json.dumps(self.title)},Name:{self.name},Objects:{_objects},Instances:{_instances},Metas:{_metas}}}"

oic = VActOIC(name)
oic.notes = notes
oic.axis = p_axis.menuItems()[p_axis.eval()]

fx_axis = vact_axis(oic.axis)
lut = {}
#idx = 0;

for point in geo.points():
    _name = point.attribValue("name")
    _type = point.attribValue("type") if b_type else force
    _module = point.attribValue("module") if b_module else module
    _parent = point.attribValue("parent") if b_parent else -1
    
    b_particle = _type in {'Particle'}
    
    _hash = _name if not b_hash else vact_hash(point.attribValue("lx"), point.attribValue("var"), b_particle)
    if _hash not in lut:
        _asset = point.attribValue("asset") if b_asset else f"{asset}SM_{_name}.SM_{_name}"
        _object = VActOIC.Object()
        _object.type = _type
        _object.asset = _asset
        #_object.meta = -1
        lut[_hash] = oic.add_object(_object)
    
    _instance = VActOIC.Instance()
    _instance.object = lut[_hash]
    _instance.parent = _parent
    #_instance.meta = -1
    _instance.transform = fx_axis(point.attribValue("P"), point.attribValue("orient"), point.attribValue("scale"), scale_correct)
    _id = oic.add_instance(_instance)
    
    #idx += 1
    #if idx > 20: break

_path = os.path.join(dir, name + ".oic")
if format in {'JSON'}:
    with open(_path, "w", encoding='utf-8') as file:
        file.write(oic.json())
        file.close()