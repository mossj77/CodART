from typing import Optional
from antlr4 import FileStream, ParseTreeWalker
from antlr4.TokenStreamRewriter import TokenStreamRewriter

from gen.java.JavaLexer import JavaLexer
from .utils_listener_fast import *
from enum import Enum


class ScopeType(Enum):
    PACKAGE = 0
    CLASS = 1
    METHOD = 2
    STATIC_BLOCK = 3
    BLOCK_STATEMENT = 4
    CONSTRUCTOR = 5


class Scope:
    def __init__(self, name: str, scope_type: ScopeType, scope_number: int, parent=None):
        self.parent: Optional[Scope] = parent
        self.children: List[Scope] = []
        self.name = name
        self.type = scope_type
        self.scope_number = scope_number
        self.declared_vars = []
        self.used_vars = []

    def __str__(self):
        return f"scope: {self.name} {self.type}"


class ScopeListener(UtilsListener):
    def __init__(self, filename: str):
        super().__init__(filename)
        self.root: Optional[Scope] = None
        self.current_scope: Optional[Scope] = None

    def enterPackageDeclaration(self, ctx:JavaParser.PackageDeclarationContext):
        super().enterPackageDeclaration(ctx)
        self.root = Scope(ctx.qualifiedName().getText(), ScopeType.PACKAGE, 0)
        self.current_scope = self.root

    def exitCompilationUnit(self, ctx:JavaParser.CompilationUnitContext):
        super().exitCompilationUnit(ctx)
        self.current_scope = None

    def enterClassDeclaration(self, ctx: JavaParser.ClassDeclarationContext):
        super().enterClassDeclaration(ctx)

        if self.current_scope is None:
            return

        scope = Scope(ctx.IDENTIFIER().getText(), ScopeType.CLASS, self.current_scope.scope_number + 1, self.current_scope)
        self.current_scope.children.append(scope)
        self.current_scope = scope

    def exitClassBody(self, ctx:JavaParser.ClassBodyContext):
        super().exitClassBody(ctx)
        self.current_scope = self.current_scope.parent

    def enterClassBodyDeclaration(self, ctx: JavaParser.ClassBodyDeclarationContext):
        super().enterClassBodyDeclaration(ctx)
        if self.current_scope is None:
            return

        if ctx.STATIC() is not None:
            scope = Scope("STATIC", ScopeType.STATIC_BLOCK, self.current_scope.scope_number + 1, self.current_scope)
            self.current_scope.children.append(scope)
            self.current_scope = scope
            return

        if ctx.block() is None:
            return

        scope = Scope("NON_STATIC", ScopeType.BLOCK_STATEMENT, self.current_scope.scope_number + 1, self.current_scope)
        self.current_scope.children.append(scope)
        self.current_scope = scope

    def exitClassBodyDeclaration(self, ctx:JavaParser.ClassBodyDeclarationContext):
        if self.current_scope.type == ScopeType.BLOCK_STATEMENT \
                or self.current_scope.type == ScopeType.STATIC_BLOCK:
            self.current_scope = self.current_scope.parent

    def enterMethodBody(self, ctx: JavaParser.MethodBodyContext):
        super().enterMethodBody(ctx)
        if self.current_scope is None:
            return

        scope = Scope(self.current_method_identifier, ScopeType.METHOD, self.current_scope.scope_number + 1,
                      self.current_scope)
        self.current_scope.children.append(scope)
        self.current_scope = scope
        setattr(self.current_method, "scope", scope)

    def exitMethodBody(self, ctx:JavaParser.MethodBodyContext):
        super().enterMethodBody(ctx)
        self.current_scope = self.current_scope.parent

    def enterConstructorDeclaration(self, ctx: JavaParser.ConstructorDeclarationContext):
        super().enterConstructorDeclaration(ctx)
        scope = Scope(ctx.IDENTIFIER().getText(), ScopeType.CONSTRUCTOR, self.current_scope.scope_number + 1,
                      self.current_scope)
        self.current_scope.children.append(scope)
        self.current_scope = scope
    #
    # def exitConstructorDeclaration(self, ctx: JavaParser.ConstructorDeclarationContext):
    #     super().exitConstructorDeclaration(ctx)
    #     self.current_scope = self.current_scope.parent

    def enterBlockStatement(self, ctx:JavaParser.BlockStatementContext):
        super().enterBlockStatement(ctx)
        if self.current_scope is None:
            return

        if self.current_scope.type == ScopeType.CONSTRUCTOR:
            return

        scope = Scope("BLOCK", ScopeType.BLOCK_STATEMENT, self.current_scope.scope_number + 1,
                      self.current_scope)
        self.current_scope.children.append(scope)
        self.current_scope = scope

    def exitBlockStatement(self, ctx:JavaParser.BlockStatementContext):
        super().exitBlockStatement(ctx)
        self.current_scope = self.current_scope.parent

    def enterStatement(self, ctx:JavaParser.StatementContext):
        super().enterStatement(ctx)
        if self.current_scope is None:
            return

        if ctx.IF():
            self.current_scope.name = "IF"
            return
        if ctx.ELSE():
            self.current_scope.name = "ELSE"
            return
        if ctx.SWITCH():
            self.current_scope.name = "SWITCH"
            return
        if ctx.FOR():
            self.current_scope.name = "FOR"
            return
        if ctx.WHILE():
            self.current_scope.name = "WHILE"
            return
        if ctx.DO():
            self.current_scope.name = "DO"
            return
        if ctx.TRY():
            self.current_scope.name = "TRY"
            return

    def enterVariableDeclarator(self, ctx: JavaParser.VariableDeclaratorContext):
        super().enterVariableDeclarator(ctx)
        if self.current_local_var_type is None:
            return

        self.current_scope.declared_vars.append(self.current_method.body_local_vars_and_expr_names[-1])

    # def exitFieldDeclaration(self, ctx: JavaParser.FieldDeclarationContext):
    #     super().exitFieldDeclaration(ctx)
    #     self.current_scope.declared_vars.append(self.package.classes[self.current_class_identifier].fields[field.name])
    #     self.field_enter_count -= 1
    #     if self.current_class_identifier is not None and self.field_enter_count == 0:
    #         for i in range(len(self.current_field_ids)):
    #             field_id = self.current_field_ids[i]
    #             dims = self.current_field_dims[i]
    #             field_init = self.current_field_inits[i]
    #             var_ctx = self.current_field_var_ctxs[i]
    #             field = Field(
    #                 package_name=self.package.name,
    #                 class_name=self.current_class_identifier,
    #                 parser_context=self.current_field_decl[2],
    #                 filename=self.filename,
    #                 file_info=self.file_info
    #             )
    #             field.modifiers = self.current_field_decl[0]
    #             field.modifiers_parser_contexts = self.current_field_decl[3]
    #             field.datatype = self.current_field_decl[1] + dims
    #             field.name = field_id
    #             field.initializer = field_init
    #             field.neighbor_names = [x for x in self.current_field_ids if x != field_id]
    #             field.all_variable_declarator_contexts = self.current_field_var_ctxs
    #             field.index_in_variable_declarators = i
    #             self.package.classes[self.current_class_identifier].fields[field.name] = field
    #         self.current_field_decl = None


def get_program2(source_files: list, print_status = False) -> Program:
    program = Program()
    listener: Optional[ScopeListener] = None
    for filename in source_files:
        if print_status:
            print("Parsing " + filename)
        stream = FileStream(filename, encoding='utf8')
        lexer = JavaLexer(stream)
        token_stream = CommonTokenStream(lexer)
        parser = JavaParser(token_stream)
        tree = parser.compilationUnit()
        listener = ScopeListener(filename)
        walker = ParseTreeWalker()
        walker.walk(listener, tree)

        if not listener.package.name in program.packages:
            program.packages[listener.package.name] = listener.package
        else:
            for classes_name in listener.package.classes:
                program.packages[listener.package.name].classes[classes_name]=listener.package.classes[classes_name]
    # if listener is not None:
    #     setattr(program, "scope", listener.root)
    return program

if __name__ == '__main__':
    filename = "/home/loop/IdeaProjects/Sample/src/sample2/Test4.java"
    program = get_program2([filename])
    print()