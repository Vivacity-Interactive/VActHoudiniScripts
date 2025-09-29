import json, pathlib, re, hou

MAX_INT = 1_000_000_000_000

class _Settings:
    def __init__(self):
        self.dir_in = "C:\Projects\VFX\90s_Breakway\_data\lidar\_tmp"
        self.regex_filter = r'swissalti3d_(?:\d+)_(\d+)-(\d+)_(?:\d+)_(\d+)_(\d+).tif'
        self.regex_group = (1,2)
        self.prefix = "HF_"
        self.geo_node_name = "Swiss"
        self.hf_node_name = "%X%_$1_$2"
        self.size_correct = 4
        self.into = '/obj/Lib_Lidar'
        self.dsize = 1000
        self.max_raydist = 4000
        self.samples = 4033
        self.x_group = 2
        self.z_group = 1
        self.x_center = None
        self.z_center = None
        self.b_erode = True
        self.erode_ability = 0.4
        self.erode_flow = 0.2
        self.erode_seed = 0.4
        self.b_erode_export = False
        self.erode_export_dir = '$HIP/tex'

class VActLoadHFF:
    def do_execute(self, context, settings):
        _hff_node_id = 'heightfield_file'
        _geo_node_id = 'geo'
        _trs_node_id = 'heightfield_xform'
        _mrg_node_id = 'merge'
        _null_node_id = 'null'
        _cache_node_id = 'filecache'
        _hfe_node_id = 'heightfield_erode'
        _vact_hfee_node_id = 'vact::vact_heightfield_texture_export'
        _hfp_node_id = 'heightfield_project'
        _hf_node_id = 'heightfield'

        _hfe = None 
        _hfee = None
        _last = None

        _dr = -1.5
        _dc = 2.0
        _n = 0

        _x_size = 0
        _z_size = 0

        x_center = settings.x_center
        z_center = settings.z_center

        _into = hou.node(settings.into)

        b_valid = _into and (_into.type().category().name() == 'Manager' or _into.type().name() == 'subnet')
        if not b_valid: raise hou.Error("no valid into node a Manager or a subnet.")

        _dir = pathlib.Path(settings.dir_in) 
        _regex = re.compile(settings.regex_filter)
        _hf_node_name = settings.hf_node_name.replace("%X%",settings.geo_node_name)

        b_valid = _dir and _regex and _hf_node_name
        if not b_valid: raise hou.Error("no valid director, regex or name.")

        _geo = _into.createNode(_geo_node_id, settings.prefix + settings.geo_node_name)
        _merge = _geo.createNode(_mrg_node_id, "MRG_" + settings.geo_node_name)
        _trs0 = _geo.createNode(_trs_node_id, "TRS_" + settings.geo_node_name)
        _last = _hfp = _geo.createNode(_hfp_node_id, "HF_Project_" + settings.geo_node_name)
        
        _hf0 = _geo.createNode(_hf_node_id, "HF_" + settings.geo_node_name)
        _hf0.parm('divisionmode').set('maxaxis')
        _hf0.parm('gridsamples').set(settings.samples)
        
        if settings.b_erode:
            _last = _hfe = _geo.createNode(_hfe_node_id, "HF_Erode_" + settings.geo_node_name)            
            
            _hfe.parm('erodability').set(settings.erode_ability)
            _hfe.parm('flow').set(settings.erode_flow)
            _hfe.parm('seed').set(settings.erode_seed)
            _hfe.setNextInput(_hfp)

            if settings.b_erode_export:
                _hfee = _geo.createNode(_vact_hfee_node_id, "HF_Export_" + settings.geo_node_name)
                _expr = f'ch("../{_hf0.name()}/gridsamples")'
                _hfee.parm('texresx').setExpression(_expr, language=hou.exprLanguage.Hscript)
                _hfee.parm('texresy').setExpression(_expr, language=hou.exprLanguage.Hscript)
                _hfee.parm('nameout').set(settings.geo_node_name)
                _hfee.parm('dirtexout').set(settings.erode_export_dir)
        
        _fc = _geo.createNode(_cache_node_id, "CACHE_" + settings.geo_node_name)
        _out = _geo.createNode(_null_node_id, "OUT")

        _fc.parm('trange').set('off')
        _hfp.parm('maxraydist').set(settings.max_raydist)
        
        _trs0.setNextInput(_merge)
        _hfp.setNextInput(_hf0)
        _hfp.setNextInput(_trs0)
        _fc.setNextInput(_last)

        if _hfee:
            _hfee.setNextInput(_fc)
            _out.setNextInput(_hfee)
        else: _out.setNextInput(_fc)

        for file in _dir.iterdir():
            if not file.is_file(): continue
            _match = _regex.match(file.name)
            if _match:
                _n += 1
                _path = str(file.resolve())
                _name = _hf_node_name
                for _group in settings.regex_group:
                    _var = f"${_group}"
                    _name = _name.replace(_var,_match.group(_group))

                _x = int(_match.group(settings.x_group))
                _z = int(_match.group(settings.z_group))

                x_center = _x if x_center is None else x_center
                z_center = _z if z_center is None else z_center

                x = (_x - x_center) * settings.dsize
                z = (_z - z_center) * settings.dsize

                _x_size = max(_x_size, x)
                _z_size = max(_z_size, z)

                print((_name, _path, (x, 0, z)))

                _hf = _geo.createNode(_hff_node_id, "HFF_" + _name)
                _hf.parm('filename').set(_path)
                _hf.parm('size').set(settings.dsize + settings.size_correct)
                
                _trs = _geo.createNode(_trs_node_id, "TRS_" + _name)
                _trs.parm('tx').set(x)
                _trs.parm('tz').set(z)
                
                _trs.setNextInput(_hf)
                _merge.setNextInput(_trs)
                
                _hf.setPosition(hou.Vector2(_n*_dc, _dr))
                _trs.setPosition(hou.Vector2(_n*_dc, _dr*2))
        
        _hf_geo = _merge.geometry()
        bbox = _hf_geo.boundingBox()
        centroid_x = -(bbox.minvec().x() + bbox.maxvec().x()) / 2
        centroid_y = bbox.minvec().y()
        centroid_z = -(bbox.minvec().z() + bbox.maxvec().z()) / 2
        _trs0.parm('heightoffset').set(centroid_y)
        _trs0.parm('tx').set(centroid_x)
        _trs0.parm('tz').set(centroid_z)

        _hf0.parm('sizex').set(_x_size)
        _hf0.parm('sizey').set(_z_size)

        _hf0.setPosition(hou.Vector2(0.5*_n*_dc - _dc, _dr*5))
        _merge.setPosition(hou.Vector2(0.5*_n*_dc, _dr*4))
        _trs0.setPosition(hou.Vector2(0.5*_n*_dc, _dr*5))
        _hfp.setPosition(hou.Vector2(0.5*_n*_dc, _dr*6))
        if _hfe:
            _hfe.setPosition(hou.Vector2(0.5*_n*_dc, _dr*7))
            _fc.setPosition(hou.Vector2(0.5*_n*_dc, _dr*8))
            if _hfee:
                _hfee.setPosition(hou.Vector2(0.5*_n*_dc, _dr*9))
                _out.setPosition(hou.Vector2(0.5*_n*_dc, _dr*11))
            else: _out.setPosition(hou.Vector2(0.5*_n*_dc, _dr*10))
        else:
            _fc.setPosition(hou.Vector2(0.5*_n*_dc, _dr*7))
            _out.setPosition(hou.Vector2(0.5*_n*_dc, _dr*9))
        
        _out.setDisplayFlag(True)

settings = _Settings()

selection = hou.selectedNodes()

operator = VActLoadHFF()
operator.do_execute(selection, settings)