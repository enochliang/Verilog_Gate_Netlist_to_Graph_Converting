import re
from lxml import etree
#import xml.etree.ElementTree as ET
import xml.dom.minidom

#==============================================================#
# Description:                                                 #
#     Convert a signal hierarchy table in <vcd file> to a      #
#     sig_tree <xml file>                                      #
#--------------------------------------------------------------#
# Input:  ooo.vcd                                              #
# Output: ooo.xml                                              #
#==============================================================#


class ParsingVCD:
    def __init__(self,vcd_path,ast_path,output_file):
        self.sig_tree = etree.ElementTree(etree.Element("root"))
        self.sig_tree_root = self.sig_tree.getroot()
        self.vcd_file = vcd_path
        self.xml_file = output_file
        self.ast_file = ast_path
        self.ast_root = etree.parse(self.ast_file).getroot()

    ################# Function Definition ################

    # Prettify XML Output from A String
    def pretty_print_xml_minidom(self,xml_string):
       dom = xml.dom.minidom.parseString(xml_string)
       pretty_xml = dom.toprettyxml(indent="  ")
       pretty_xml = "\n".join(line for line in pretty_xml.split("\n") if line.strip())
       #print(pretty_xml)
       return pretty_xml

    # Search Struct Information
    def FindStruct(self,in_text,level):
        struct_list = re.findall("\n"+"@"*level+"\$scope struct .*? \$end",in_text)
        struct_list = [ re.sub(" +", " ", i).split(' ')[2] for i in struct_list]
        return struct_list
    # Search Struct Contents
    def FindStructContent(self,in_text,name,level):
        struct_scope = re.findall("\n"+"@"*(level)+"\$scope struct "+name.replace("[",'\[').replace("]",'\]')+" [\w\W]*?\n"+"@"*(level)+"\$upscope \$end",in_text)[0]
        struct_scope = "\n"+"\n".join(struct_scope.split("\n")[2:-1])
        return struct_scope
    def FindStructTextBlock(self,in_text,name,level):
        struct_scope = re.findall("\n"+"@"*(level)+"\$scope struct "+name.replace("[",'\[').replace("]",'\]')+" [\w\W]*?\n"+"@"*(level)+"\$upscope \$end",in_text)[0]
        return struct_scope
    # Search Var Information
    def FindVars(self,in_text,level):
        var_list = re.findall("\n"+"@"*level+"\$var .*? \$end",in_text)
        var_list = [ re.sub(" +", " ", i).split(' ')[2:5] for i in var_list]
        return var_list
    # Search Module Contents
    def FindModuleContent(self,in_text,name,level):    
        module_scope = re.findall("\n"+"@"*(level)+"\$scope module "+name.replace("[",'\[').replace("]",'\]')+" [\w\W]*?\n"+"@"*(level)+"\$upscope \$end",in_text)[0]
        module_scope = "\n"+"\n".join(module_scope.split("\n")[2:-1])
        return module_scope
    # Search Module Information
    def FindModuleInfo(self,in_text,level):
        #=====================================================#
        # Given: a piece of VCD Content, level                #
        # Goal: Find the names of modules under this level    #
        #=====================================================#
        module_info = re.findall("\n"+"@"*level+"\$scope module[\w\W]*? \$end",in_text)
        module_info = [ re.sub(" +", " ", i).split(' ')[2] for i in module_info]
        return module_info

    # TREE BUILDING
    # Put Structs into the Module Hierachy Tree
    def iter_PutStruct(self,in_text,level=1,hier=''):
        struct = self.FindStruct(in_text,level)
        # Go to the new module node
        if level == 1:
            module = self.sig_tree_root.find(".//module[@hier='"+hier+"']")
        else:
            module = self.sig_tree_root.find(".//struct[@hier='"+hier+"']")
        for st in struct:
            child = etree.SubElement(module, "struct")
            child.set("name", st)
            child.set("hier", hier+"."+st)
        for st in struct:
            s = self.FindStructContent(in_text,st,level)
            var = self.FindVars(s,level+1)
            module = self.sig_tree_root.find(".//struct[@hier='"+hier+"."+st+"']")
            # Adding...
            for v in var:
                child = etree.SubElement(module, "var")
                child.set("name", v[2])
                child.set("hier", hier+"."+st+"."+v[2])
                child.set("code", v[1])
                child.set("size", v[0])
            self.iter_PutStruct(s,level+1,hier+"."+st)

    # Building Module Hierachy Tree
    def iter_PutNode(self,in_text,level=1,hier=''):
        #=====================================================#
        # Given: a piece of VCD Content, level, hierachy name #
        # Goal: Add module nodes to the tree under this level #
        #=====================================================#
        modules = self.FindModuleInfo(in_text,level)
        # Add module Nodes on level N
        for name in modules:
            if level == 1:
                # Go to root
                child = etree.SubElement(self.sig_tree_root, "module")
                child.set("name", name)
                child.set("hier", name)
                child.set("level", str(level))
            else:
                # Go to the parent node
                module = self.sig_tree_root.find(".//module[@hier='"+hier+"']")
                # Add a child node
                child = etree.SubElement(module, "module")
                child.set("name", name)
                child.set("hier", hier+"."+name)
                child.set("level", str(level))
        # Add var Nodes under the nodes we just added under level N
        for name in modules:
            s = self.FindModuleContent(in_text,name,level)
            var = self.FindVars(s,level+1)
            # Go to the new module node
            if level == 1:
                module = self.sig_tree_root.find(".//module[@hier='"+name+"']")
            else:
                module = self.sig_tree_root.find(".//module[@hier='"+hier+"."+name+"']")
            # Adding...
            for v in var:
                child = etree.SubElement(module, "var")
                child.set("name", v[2])
                child.set("hier", hier+"."+name+"."+v[2])
                child.set("code", v[1])
                child.set("size", v[0])
        # Add structs
        for name in modules:
            s = self.FindModuleContent(in_text,name,level)
            strt = self.FindStruct(s,level+1)
            for struct in strt:
                struct_text = self.FindStructTextBlock(s,struct,level+1)
                struct_text = struct_text.replace("\n"+"@"*level,"\n")
                # Add structs iteratively
                self.iter_PutStruct(struct_text,level=1,hier=hier+"."+name)
        # Adding modules iteratively
        for name in modules:
            s = self.FindModuleContent(in_text,name,level)
            if level == 1:
                self.iter_PutNode(s,level=level+1,hier=name)
            else:
                self.iter_PutNode(s,level=level+1,hier=hier+"."+name)




    # TREE MODIFICATION
    def RUN_Parsing(self):
    # Get VCD Content
        with open(self.vcd_file,"r") as f:
            content = f.read()
        s = re.findall(r' \$scope[\W\w]*\n \$upscope \$end',content)[0]
        for i in range(1,21):
            s = s.replace("\n"+' '*i+"$","\n"+'@'*i+"$")
        s = "\n@"+s[1:]

    # Building <sig_tree>
        self.iter_PutNode(s,level=1,hier='')



    # Tag Modification
    def tag_modification(self):
        # change the tags for the module in <sig_tree> which is a package in <ast>
        modules = self.sig_tree_root.findall(".//module")
        for m in modules:
            if "_pkg" in m.attrib["name"]:
                m.tag = "package"

        # change the tags for the module in <sig_tree> which is a real instance in <ast>
        ast_tree = etree.parse(self.ast_file)
        self.ast_root = ast_tree.getroot()
        cell_list = [i.attrib["name"] for i in self.ast_root.findall(".//cell")]
        for instance in self.sig_tree_root.findall(".//module"):
            if instance.attrib["name"] in cell_list:
                submodname = self.ast_root.find(".//cell[@name='"+instance.attrib["name"]+"']").attrib["submodname"]
                origName = self.ast_root.find(".//module[@name='"+submodname+"']").attrib["origName"]
                instance.tag = "instance"
                instance.set("origName",origName)
                instance.set("submodname",submodname)

        # marking parameter & localparam for the <var> in <sig_tree>
        for instance in self.sig_tree_root.findall(".//instance"):
            for var in instance.findall("./var")+instance.findall("./module/var"): # going all the vars in instances

                submodname = self.ast_root.find(".//cell[@name='"+instance.attrib["name"]+"']").attrib["submodname"]

                # If the var is in vcd, but in the AST. it means ...
                if self.ast_root.find(".//module[@name='"+submodname+"']/var[@name='"+var.attrib['name']+"']") is None:

                    if "[" in var.attrib['name']: # the var is an array
                        target = self.ast_root.find(".//module[@name='"+submodname+"']//var[@name='"+var.attrib['name'].split('[')[0]+"']")

                        if target is None: # array name doesn't exist in the AST
                            #print("<array> name ["+var.attrib['name']+"] doesn't exist in ["+submodname+"]")
                            var.attrib["ommitted"] = "true"
                            # Unmark to test
                            """if self.ast_root.find(".//var[@name='"+var.attrib['name'].split('[')[0]+"']") is None:
                                print("yes")
                            else:
                                print("no")"""
                        elif 'param' in target.attrib:
                            var.attrib["param"] = "true"
                        elif 'localparam' in target.attrib:
                            var.attrib["localparam"] = "true"
                        else: # not a param

                            if 'vartype' in target.attrib:
                                if target.attrib["vartype"] == "integer":
                                    var.tag = 'integer'
                                elif target.attrib["vartype"] == "int":
                                    var.tag = 'int'
                                elif target.attrib["vartype"] == "longint":
                                    var.tag = 'longint'

                            if 'dir' in target.attrib:
                                if target.attrib["dir"] == "input":
                                    var.attrib["dir"] = 'input'
                                elif target.attrib["dir"] == "output":
                                    var.attrib["dir"] = 'output'
                            pass

                    else: # var is a normal packed var, and it's ommitted by verilog parser
                        target = self.ast_root.find(".//module[@name='"+submodname+"']//var[@name='"+var.attrib['name']+"']")
                        if target is None: # var name doesn't exist in the AST
                            #print("<var> name ["+var.attrib['name']+"] doesn't exist in ["+submodname+"]")
                            var.attrib["ommitted"] = "true"
                            # Unmark to test
                            """if self.ast_root.find(".//var[@name='"+var.attrib['name']+"']") is None:
                                print("yes")
                            else:
                                print("no")"""
                        elif 'param' in target.attrib:
                            var.attrib["param"] = "true"
                        elif 'localparam' in target.attrib:
                            var.attrib["localparam"] = "true"
                        else:
                            #print(var.attrib['hier'])
                            if 'vartype' in target.attrib:
                                if target.attrib["vartype"] == "integer":
                                    var.tag = 'integer'
                                elif target.attrib["vartype"] == "int":
                                    var.tag = 'int'
                                elif target.attrib["vartype"] == "longint":
                                    var.tag = 'longint'

                            if 'dir' in target.attrib:
                                if target.attrib["dir"] == "input":
                                    var.attrib["dir"] = 'input'
                                elif target.attrib["dir"] == "output":
                                    var.attrib["dir"] = 'output'
                            pass
                # If the var is in both <vcd> and <AST>
                else:
                    if 'param' in self.ast_root.find(".//module[@name='"+submodname+"']/var[@name='"+var.attrib['name']+"']").attrib:
                        #print(var.attrib['name'])
                        var.attrib["param"] = "true"
                    elif 'localparam' in self.ast_root.find(".//module[@name='"+submodname+"']/var[@name='"+var.attrib['name']+"']").attrib:
                        var.attrib["localparam"] = "true"
                    # Real signal
                    else:
                        pass

                    if 'vartype' in self.ast_root.find(".//module[@name='"+submodname+"']/var[@name='"+var.attrib['name']+"']").attrib:
                        if self.ast_root.find(".//module[@name='"+submodname+"']/var[@name='"+var.attrib['name']+"']").attrib["vartype"] == "integer":
                            var.tag = 'integer'
                        elif self.ast_root.find(".//module[@name='"+submodname+"']/var[@name='"+var.attrib['name']+"']").attrib["vartype"] == "int":
                            var.tag = 'int'
                        elif self.ast_root.find(".//module[@name='"+submodname+"']/var[@name='"+var.attrib['name']+"']").attrib["vartype"] == "longint":
                            var.tag = 'longint'

                    if 'dir' in self.ast_root.find(".//module[@name='"+submodname+"']/var[@name='"+var.attrib['name']+"']").attrib:
                        if self.ast_root.find(".//module[@name='"+submodname+"']/var[@name='"+var.attrib['name']+"']").attrib["dir"] == "input":
                            var.attrib["dir"] = 'input'
                        elif self.ast_root.find(".//module[@name='"+submodname+"']/var[@name='"+var.attrib['name']+"']").attrib["dir"] == "output":
                            var.attrib["dir"] = 'output'

        # Changing <struct> tags to <var>
        t = []
        for var in self.sig_tree_root.findall(".//struct"):
            if not "struct" in self.sig_tree.getpath(var.getparent()):
                t.append(var)
        for var in t:
                var.tag = "var_t"
        for var in self.sig_tree_root.findall(".//var_t"):
            if not var.getchildren() == []:
                for sub_var in var.iter():
                    sub_var.tag = "varx"
            var.tag = "var"

        cell_root = self.ast_root.find(".//cells")
        cell_list = []
        ins_dict = {}
        for cell in cell_root.findall(".//cell"):
            cell_list.append(cell.attrib["hier"])
        for ins in self.sig_tree_root.findall(".//instance"):
            hier = ins.attrib["hier"][4:]
            ins_dict[hier] = ''
            if hier in cell_list:
                ins_dict[hier] = cell_root.find(".//cell[@hier='"+hier+"']").attrib["submodname"]
            else:
                cnt = 0
                for c in cell_list:
                    if hier.split(".")[-1] == c.split(".")[-1]:
                        cnt = cnt + 1
                if cnt == 1:
                    hier


        print(ins_dict)
        # mark the unused variables
        #for var in self.sig_tree_root.findall(".//var"):
        #    # var is not used
        #    if "unused_" in var.attrib['name']:
        #        var.tag = "unused_var"
        #for struct in self.sig_tree_root.findall(".//struct"):
        #    # struct is not used
        #    if "unused_" in struct.attrib['name']:
        #        struct.tag = "unused_struct"

        # Output Hierachy Tree
        xml_data = etree.tostring(self.sig_tree_root, encoding="utf-8")
        txt = self.pretty_print_xml_minidom(xml_data)

        with open(self.xml_file,"w") as f:
            f.write(txt)




################ MAIN Function #################
if __name__ == "__main__":

    vcd_path = "sim.vcd"
    ast_path = "ast/Vibex_simple_system.xml"
    output_file = "vcd_sig.xml"

    parse = ParsingVCD(vcd_path,ast_path,output_file)

    parse.RUN_Parsing()
    parse.tag_modification()

