from lxml import etree
import pandas as pd

class ASTParser:

    # It's a parser to parse RTL-AST.

    def __init__(self, filename):
        self.ast = etree.parse(filename)
        self.tag_list = self._get_unique_tags()
        self.children_structure_dict = self._get_child_node_structure()
        self.children_const_structure_dict = self._get_child_node_const_structure() 
        self.vartype_list = self._get_vartype_list()
        self.tag_under_module = self._check_tag_under_module()
        self.gen_block_name_list = self._check_gen_block_name()

    # List all kinds of tag in the AST without repetition.
    def _get_unique_tags(self,output=False):
        tags = set()
        for node in self.ast.getroot().iter():
            tags.add(node.tag)
        if output:
            for tag in tags:
                print(tag)
        return list(tags)

    # Construct a dictionary with all kinds of tag as key.
    # The value of each tag is a list of all possible child nodes structure.
    def _get_child_node_structure(self,output=False):
        children_structure_dict = {}
        for tag in self.tag_list:
            children_structure_dict[tag] = []

        for tag in self.tag_list:
            for node in self.ast.getroot().findall(".//"+tag):
                child_struct = [child.tag for child in node.getchildren()]
                if not child_struct in children_structure_dict[tag]:
                    children_structure_dict[tag].append(child_struct)
        if output:
            print(children_structure_dict)
        return children_structure_dict


    # 
    def _get_child_node_const_structure(self,output=False):
        tags = self.children_structure_dict.keys()
        children_const_structure_dict = self.children_structure_dict.copy()
        for key in tags:
            size = [len(struct) for struct in self.children_structure_dict[key]]
            for s in size:
                if s != size[0]:
                    del children_const_structure_dict[key]
                    break
        if output:
            print(children_const_structure_dict.keys())
        return children_const_structure_dict
                

    # List all different kinds of "vartype"
    def _get_vartype_list(self,output=False):
        var_type_set = set()
        for var in self.ast.getroot().findall(".//var"):
            var_type_set.add(var.attrib["vartype"])
        if output:
            print(list(var_type_set))
        return list(var_type_set)

    # Drop the tags never be unger <module>
    def _check_tag_under_module(self,output=False):
        tag_under_module_set = set()
        for tag in self.tag_list:
            for node in self.ast.getroot().findall(".//"+tag):
                if "module" in self.ast.getpath(node.getparent()):
                    tag_under_module_set.add(tag)
                    break
        if output:
            for tag in tag_under_module_set:
                print(tag)
        return list(tag_under_module_set)

    def _check_gen_block_name(self,output=False):
        gen_block_name_set = set()
        for node in self.ast.getroot().findall(".//begin"):
            if "name" in node.attrib.keys():
                gen_block_name_set.add(node.attrib['name'])
        if output:
            for blk_name in gen_block_name_set:
                print(blk_name)
        return list(gen_block_name_set)

    # 
    def database_construction(self,output=False):
        data = pd.DataFrame(index=self.tag_list)
        data['under_module'] = data.index.isin(self.tag_under_module).astype(int)
        data['children_const_structure'] = data.index.isin(self.children_const_structure_dict.keys()).astype(int)
        #data[''] = data.index.isin(self.tag_under_module).astype(int)
        if output:
            print(data)

AST = ASTParser("./ast/Vibex_top.xml")
AST.database_construction()
