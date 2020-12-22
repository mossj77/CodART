import utils_listener
import utils

def pullup_field(source_filenames: list,
                 package_name: str,
                 superclass_name: str,
                 field_name: str,
                 filename_mapping = lambda x: (x[:-5] if x.endswith(".java") else x) + ".re.java") -> bool:

    program = utils.get_program(source_filenames)
    if package_name not in program.packages \
            or superclass_name not in program.packages[package_name].classes \
            or field_name in program.packages[package_name].classes[superclass_name].fields:
        return False

    superclass: utils_listener.Class = program.packages[package_name].classes[superclass_name]
    superclass_body_start = utils_listener.TokensInfo(superclass.parser_context.classBody())
    print(superclass_body_start.start)
    superclass_body_start.stop = superclass_body_start.start # Start and stop both point to the '{'

    fields_to_remove = []
    for pn in program.packages:
        p: utils_listener.Package = program.packages[pn]
        for cn in p.classes:
            c: utils_listener.Class = p.classes[cn]
            if superclass_name == c.superclass_name and field_name in c.fields:
                fields_to_remove.append(c.fields[field_name])

    if len(fields_to_remove) == 0:
        return False

    is_public = False
    datatype = fields_to_remove[0].datatype
    for field in fields_to_remove:
        field: utils_listener.Field = field
        if field.datatype != datatype:
            return False
        is_public = is_public or "public" in field.modifiers

    rewriter = utils.Rewriter(program, filename_mapping)

    rewriter.insert_after(superclass_body_start, "\n\t" + ("public " if is_public else "protected ") + datatype + " " + field_name + ";")

    for field in fields_to_remove:
        if len(field.neighbor_names) == 0:
            rewriter.replace(field.get_tokens_info(), "")
        else:
            i = field.index_in_variable_declarators
            var_ctxs = field.all_variable_declarator_contexts
            if i == 0:
                to_remove = utils_listener.TokensInfo(var_ctxs[i])
                to_remove.stop = utils_listener.TokensInfo(var_ctxs[i + 1]).start - 1 # Include the ',' after it
                rewriter.replace(to_remove, "")
            else:
                to_remove = utils_listener.TokensInfo(var_ctxs[i])
                to_remove.start = utils_listener.TokensInfo(var_ctxs[i - 1]).stop + 1 # Include the ',' before it
                rewriter.replace(to_remove, "")

    rewriter.apply()
    return True

if __name__ == "__main__":
    print("Testing pullup_field...")
    if pullup_field(["tests/pullup_field/test1.java", "tests/pullup_field/test2.java"], "pullup_field_test1", "A", "a"):
        print("Success!")
    else:
        print("Cannot refactor.")
