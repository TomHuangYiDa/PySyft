# stdlib
from enum import Enum


class GAMMA_TENSOR_OP(Enum):
    # Numpy ArrayLike
    NOOP = "noop"
    ADD = "add"
    SUBTRACT = "subtract"
    MULTIPLY = "multiply"
    TRUE_DIVIDE = "true_divide"
    MATMUL = "matmul"
    RMATMUL = "rmatmul"
    GREATER = "greater"
    GREATER_EQUAL = "greater_equal"
    EQUAL = "equal"
    NOT_EQUAL = "not_equal"
    LESS = "less"
    LESS_EQUAL = "less_equal"
    EXP = "exp"
    LOG = "log"
    TRANSPOSE = "transpose"
    SUM = "sum"
    ONES_LIKE = "ones_like"
    ZEROS_LIKE = "zeros_like"
    RAVEL = "ravel"
    RESIZE = "resize"
    COMPRESS = "compress"
    SQUEEZE = "squeeze"
    ANY = "any"
    ALL = "all"
    LOGICAL_AND = "logical_and"
    LOGICAL_OR = "logical_or"
    POSITIVE = "positive"
    NEGATIVE = "negative"
    MEAN = "mean"
    STD = "std"
    DOT = "dot"
    SQRT = "sqrt"
    ABS = "abs"
    CLIP = "clip"
    TRACE = "trace"
    MIN = "min"
    MAX = "max"
    REPEAT = "repeat"
    # Our Methods
    RECIPROCAL = "reciprocal"
    FLATTEN_C = "flatten_c"
    FLATTEN_A = "flatten_a"
    FLATTEN_F = "flatten_f"
    FLATTEN_K = "flatten_k"
