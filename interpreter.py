import sys, os

from exceptions import BreakException, ContinueException

sys.path.append(os.path.abspath('/'))
sys.path.append(os.path.abspath(''))

import AST
from memory import *
from visit import *

sys.setrecursionlimit(10000)


class Interpreter(object):
    def __init__(self):
        self.memory_stack: MemoryStack = MemoryStack()

    @on('node')
    def visit(self, node):
        pass

    @when(AST.BinExpr)
    def visit(self, node):
        r2 = node.right.accept(self)
        left = node.left
        if node.op == "=":
            try:
                if isinstance(left, AST.ArrayPart):
                    m = self.memory_stack.get(left.var.name)
                    introw = [i.accept(self) for i in left.introw.children]
                    if len(introw) != 1 and len(m) == 1:
                        raise Exception("Runtime expection. Wrong index.")
                    if len(introw) == 2 and len(m) < 2:
                        raise Exception("Runtime expection. Wrong index.")
                    if len(m) == 1:
                        m[0][introw[0]] = r2
                    else:
                        m[introw[0]][introw[1]] = r2
                else:
                    val = None
                    if isinstance(r2, list):
                        pass
                    self.memory_stack.set(left.name, r2)
            except (ValueError, KeyError):
                self.memory_stack.insert(left.name, r2)
            return None
        self_assign_ops = {
            '+=': lambda x, y: x + y,
            '-=': lambda x, y: x - y,
            '/=': lambda x, y: x / y,
            '*=': lambda x, y: x * y
        }
        for key in self_assign_ops:
            if key == node.op:
                val_left = self.memory_stack.get(left.name)
                try:
                    self.memory_stack.set(left.name, self_assign_ops[node.op](val_left, r2))
                except ValueError:
                    self.memory_stack.insert(left.name, self_assign_ops[node.op](val_left, r2))
                return None
        r1 = left.accept(self)
        ops = {'+': lambda x, y: self.sum_binop(x, y),
               '-': lambda x, y: x - y,
               '*': lambda x, y: self.mul_binop(x, y),
               '/': lambda x, y: x / y,
               '&&': lambda x, y: x and y,
               '||': lambda x, y: x or y,
               "!=": lambda x, y: x != y,
               ">": lambda x, y: x > y,
               "<": lambda x, y: x < y,
               ">=": lambda x, y: x >= y,
               "<=": lambda x, y: x <= y,
               "==": lambda x, y: x == y,
               ".+": lambda x, y: self.add_el_wise(x, y),
               ".*": lambda x, y: self.mul_el_wise(x, y),
               "./": lambda x, y: self.div_el_wise(x, y),
               ".-": lambda x, y: self.sub_el_wise(x, y),
               }
        op = node.op
        if isinstance(node.op, AST.LogicalOperator):
            op = node.op.accept(self)
        return ops[op](r1, r2)

    @when(AST.FloatNum)
    def visit(self, node: AST.FloatNum):
        return float(node.value)

    @when(AST.IntNum)
    def visit(self, node: AST.IntNum):
        return int(node.value)

    @when(AST.String)
    def visit(self, node: AST.String):
        return node.value

    @when(AST.Variable)
    def visit(self, node: AST.Variable):
        return self.memory_stack.get(node.name)

    @when(AST.Loop)
    def visit(self, node: AST.Loop):
        self.memory_stack.push(node.type)
        result = None
        if node.loop == 'WHILE':
            while node.condition.accept(self):
                try:
                    result = node.instruction.accept(self)
                except ContinueException:
                    continue
                except BreakException:
                    break
        else:
            array_range = node.condition
            beginning = array_range.beginning.accept(self)
            end = array_range.end.accept(self)
            try:
                self.memory_stack.set(array_range.counter.name, beginning)
            except KeyError:
                self.memory_stack.insert(array_range.counter.name, beginning)
            for counter in range(beginning, end):
                try:
                    self.memory_stack.set(array_range.counter.name, counter)
                    result = node.instruction.accept(self)
                except ContinueException:
                    continue
                except BreakException:
                    break
        self.memory_stack.pop()
        return result

    @when(AST.IfStatement)
    def visit(self, node: AST.IfStatement):
        self.memory_stack.push(node.type)
        result = None
        if node.condition.accept(self):
            result = node.instruction.accept(self)
            self.memory_stack.pop()
        else:
            self.memory_stack.pop()
            if node.elseStatement:
                result = node.elseStatement.accept(self)
        return result

    @when(AST.ElseStatement)
    def visit(self, node: AST.ElseStatement):
        self.memory_stack.push(node.type)
        result = node.instruction.accept(self)
        self.memory_stack.pop()
        return result

    @when(AST.Instruction)
    def visit(self, node: AST.Instruction):
        return node.instruction.accept(self)

    @when(AST.Program)
    def visit(self, node: AST.Program):
        self.memory_stack.push("main")
        res = None
        for ch in node.children:
            res = ch.accept(self)
        self.memory_stack.pop()
        return res

    @when(AST.Instructions)
    def visit(self, node: AST.Instructions):
        res = None
        for ch in node.children:
            res = ch.accept(self)
        return res

    @when(AST.InstructionsOpt)
    def visit(self, node: AST.InstructionsOpt):
        res = None
        for ch in node.children:
            res = ch.accept(self)
        return res

    @when(AST.Printable)
    def visit(self, node: AST.Printable):
        res = None
        for ch in node.children:
            res = ch.accept(self)
            print(res)
        return res

    @when(AST.InstructionWithArg)
    def visit(self, node: AST.InstructionWithArg):
        # todo: handle 'return'
        return node.expr.accept(self)

    @when(AST.LogicalOperator)
    def visit(self, node: AST.LogicalOperator):
        return node.op

    @when(AST.Break)
    def visit(self, node: AST.Break):
        raise BreakException()

    @when(AST.Continue)
    def visit(self, node: AST.Continue):
        raise ContinueException()

    @when(AST.Vector)
    def visit(self, node: AST.Vector):
        return [[ch.accept(self) for ch in node.row.children][::-1]]

    @when(AST.Matrix)
    def visit(self, node: AST.Matrix):
        m = []
        for r in node.rows.children:
            row = []
            for c in r.children:
                row.insert(0, c.accept(self))
            m.insert(0, row)
        return m

    @when(AST.ArrayPart)
    def visit(self, node: AST.ArrayPart):
        arg_name = node.var.name
        args = node.children[0].children
        array = self.memory_stack.get(arg_name)
        if len(args) == 1:
            x = args[0].accept(self)
            return array[0][x]
        elif len(args) == 2:
            return array[args[0].accept(self)][args[1].accept(self)]
        else:
            raise RuntimeError("Dimensions of arrays higher than 2 are not supported.")

    def sum_binop(self, x, y):
        if type(x) == type(y) == type([]):
            return self.add_el_wise(x, y)
        else:
            return x + y

    def add_el_wise(self, x, y):
        self.validate_el_wise_op(x, y)
        res = []
        for r1, r2 in zip(x, y):
            row = []
            for a, b in zip(r1, r2):
                row.append(a + b)
            res.append(row)
        return res

    def validate_el_wise_op(self, x, y):
        if len(x) != len(y) or len(x[0]) != len(y[0]):
            raise AttributeError("Wrong sizes of matrices.")
        if type(x) != type(y) or type(x) != type([]) or type(y) != type([]):
            raise AttributeError(".+ operator requires matrix.")

    def mul_el_wise(self, x, y):
        self.validate_el_wise_op(x, y)

        res = []
        for r1, r2 in zip(x, y):
            row = []
            for a, b in zip(r1, r2):
                row.append(a * b)
            res.append(row)
        return res

    def div_el_wise(self, x: list, y: list):
        self.validate_el_wise_op(x, y)

        res = []
        for r1, r2 in zip(x, y):
            row = []
            for a, b in zip(r1, r2):
                row.append(a / b)
            res.append(row)
        return res

    def sub_el_wise(self, x, y):
        self.validate_el_wise_op(x, y)

        res = []
        for r1, r2 in zip(x, y):
            row = []
            for a, b in zip(r1, r2):
                row.append(a - b)
            res.append(row)
        return res

    def mul_binop(self, x, y):
        if type(x) == type(y) == type([]):
            return self.mul_matrix(x, y)
        else:
            return x * y

    def mul_matrix(self, x, y):
        if len(x) == len(y[0]) and len(y) == len(x[0]):
            result = [[0 for i in range(len(y[0]))] for j in range(len(x))]
            for i in range(len(x)):
                for j in range(len(y[0])):
                    for k in range(len(y)):
                        result[i][j] += x[i][k] * y[k][j]
            return result
        else:
            raise Exception("Runtime expection. Matrixes do not have proper size")

    @when(AST.Eye)
    def visit(self, node: AST.Zeros):
        m = []
        args = node.arg.children
        arg1 = args[0].accept(self)
        arg2 = None
        if len(args) == 2:
            arg2 = args[1].accept(self)
        else:
            arg2 = arg1
        for i in range(0, arg2):
            l = []
            for j in range(0, arg1):
                if i == j:
                    l.append(1)
                else:
                    l.append(0)
            m.append(l)
        return m

    @when(AST.Ones)
    def visit(self, node: AST.Zeros):
        m = []
        args = node.arg.children
        arg1 = args[0].accept(self)
        arg2 = None
        if len(args) == 2:
            arg2 = args[1].accept(self)
        else:
            arg2 = arg1
        for i in range(0, arg2):
            l = []
            for j in range(0, arg1):
                l.insert(0, 1)
            m.insert(0, l)
        return m

    @when(AST.Zeros)
    def visit(self, node: AST.Zeros):
        m = []
        args = node.arg.children
        arg1 = args[0].accept(self)
        arg2 = None
        if len(args) == 2:
            arg2 = args[1].accept(self)
        else:
            arg2 = arg1
        for i in range(0, arg2):
            l = []
            for j in range(0, arg1):
                l.insert(0, 0)
            m.insert(0, l)
        return m
