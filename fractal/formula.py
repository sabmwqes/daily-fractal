"""フラクタル漸化式の生成モジュール (Expression Tree Grammar)

式木（Expression Tree）を再帰的に構築して、フラクタルの漸化式
z_{n+1} = f(z, c) をランダム生成する。

文法の概要:
  トップレベル:
    - inner(z) + c   (85%)  … Mandelbrot/Julia 標準形
    - c * inner(z)   (15%)  … 乗算型

  inner(z) の生成規則（再帰、max_depth=3）:
    - z^p             (べき乗)
    - e1 + a*e2       (加算混合)
    - a * e           (スケーリング)
    - sin(e) / cos(e) (三角関数)
    - ship(e)         (|Re|+i|Im| — Burning Ship 変換)
    - conj(e)         (複素共役)
    - z               (終端: 変数そのもの)
"""

import random
import numpy as np


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 式木ノード
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class ExprNode:
    """式木ノードの基底クラス"""

    def evaluate(self, z: np.ndarray, c: np.ndarray) -> np.ndarray:
        raise NotImplementedError

    def display(self) -> str:
        raise NotImplementedError

    def _needs_parens(self) -> bool:
        return False


class ZVar(ExprNode):
    """変数 z"""
    def evaluate(self, z, c):
        return z
    def display(self):
        return "z"


class ZCProduct(ExprNode):
    """z*c (引数混合型のターミナルノード)"""
    def evaluate(self, z, c):
        return z * c
    def display(self):
        return "z*c"
    def _needs_parens(self):
        return True


class CVar(ExprNode):
    """変数 c"""
    def evaluate(self, z, c):
        return c
    def display(self):
        return "c"


class RealConst(ExprNode):
    """実数定数"""
    def __init__(self, value: float):
        self.value = value
    def evaluate(self, z, c):
        return self.value
    def display(self):
        return f"{self.value:g}"


class Pow(ExprNode):
    """べき乗  base^exp"""
    def __init__(self, base: ExprNode, exp: float):
        self.base = base
        self.exp = exp

    def evaluate(self, z, c):
        return self.base.evaluate(z, c) ** self.exp

    def display(self):
        b = self.base.display()
        if self.base._needs_parens():
            b = f"({b})"
        return f"{b}^{self.exp:g}"

    def _needs_parens(self):
        return True


class Add(ExprNode):
    """加算  left + right"""
    def __init__(self, left: ExprNode, right: ExprNode):
        self.left = left
        self.right = right

    def evaluate(self, z, c):
        return self.left.evaluate(z, c) + self.right.evaluate(z, c)

    def display(self):
        return f"{self.left.display()} + {self.right.display()}"

    def _needs_parens(self):
        return True


class Mul(ExprNode):
    """乗算  left * right"""
    def __init__(self, left: ExprNode, right: ExprNode):
        self.left = left
        self.right = right

    def evaluate(self, z, c):
        return self.left.evaluate(z, c) * self.right.evaluate(z, c)

    def display(self):
        l_str = self.left.display()
        r_str = self.right.display()
        if isinstance(self.left, Add):
            l_str = f"({l_str})"
        if isinstance(self.right, Add):
            r_str = f"({r_str})"
        return f"{l_str}*{r_str}"

    def _needs_parens(self):
        return True


class UnaryFunc(ExprNode):
    """単項関数  sin(arg) / cos(arg)"""
    _FUNCS: dict = {
        "sin": np.sin,
        "cos": np.cos,
    }

    def __init__(self, func_name: str, arg: ExprNode):
        self.func_name = func_name
        self.arg = arg

    def evaluate(self, z, c):
        return self._FUNCS[self.func_name](self.arg.evaluate(z, c))

    def display(self):
        return f"{self.func_name}({self.arg.display()})"


class AbsReIm(ExprNode):
    """|Re(x)| + i|Im(x)|  (Burning Ship 変換)"""
    def __init__(self, arg: ExprNode):
        self.arg = arg

    def evaluate(self, z, c):
        val = self.arg.evaluate(z, c)
        return np.abs(np.real(val)) + 1j * np.abs(np.imag(val))

    def display(self):
        return f"ship({self.arg.display()})"


class Conjugate(ExprNode):
    """複素共役  conj(arg)"""
    def __init__(self, arg: ExprNode):
        self.arg = arg

    def evaluate(self, z, c):
        return np.conj(self.arg.evaluate(z, c))

    def display(self):
        return f"conj({self.arg.display()})"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 式木の生成
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def _pick_power(rng: random.Random) -> float:
    """べき乗指数を選択する (整数べき多め、たまに小数べき)"""
    if rng.random() < 0.5:
        return rng.choice([2, 2, 2, 3, 3, 4, 5])
    else:
        return round(rng.uniform(2.0, 5.0), 2)


def _generate_inner(
    rng: random.Random,
    depth: int = 0,
    max_depth: int = 3,
    terminal_factory: type = ZVar,
) -> ExprNode:
    """f(z) の内部式を再帰的に生成する

    深さが増すにつれ終端 (z) に収束しやすくなり、
    式が無限に深くなるのを防ぐ。
    ship() は depth >= 2 でのみ生成可能（浅い位置だと単調になるため）。
    terminal_factory: 終端ノードのクラス (ZVar or ZCProduct)。
    """
    # 深さ上限 → 終端
    if depth >= max_depth:
        return terminal_factory()


    # --- 選択肢と重みを構築 ---
    choices = ["pow", "add_mix", "scale", "trig", "conj"]
    weights = [0.20, 0.20, 0.12, 0.15, 0.18]

    # ship() は 対称性が著しく崩れるので，出現させない
    # if depth >= 3:
    #     choices.append("ship")
    #     weights.append(0.15)

    pick = rng.choices(choices, weights=weights)[0]

    if pick == "pow":
        # z^p  (べき乗)
        p = _pick_power(rng)
        base = _generate_inner(rng, depth + 1, max_depth, terminal_factory)
        return Pow(base, p)

    elif pick == "add_mix":
        # e1 + a*e2  (加算混合 — 微小な変形を加える)
        e1 = _generate_inner(rng, depth + 1, max_depth, terminal_factory)
        a = round(rng.uniform(0.05, 0.35), 3)
        e2 = _generate_inner(rng, depth + 1, max_depth, terminal_factory)
        return Add(e1, Mul(RealConst(a), e2))

    elif pick == "scale":
        # a * e  (スケーリング — 振幅調整)
        a = round(rng.uniform(0.3, 1.5), 2)
        return Mul(RealConst(a), _generate_inner(rng, depth + 1, max_depth, terminal_factory))

    elif pick == "trig":
        # sin(e) / cos(e)  (三角関数 — 周期的な構造を追加)
        func = rng.choice(["sin", "cos"])
        return UnaryFunc(func, _generate_inner(rng, depth + 1, max_depth, terminal_factory))

    elif pick == "ship":
        # ship(e)  (Burning Ship 変換 — 折り畳み対称性)
        return AbsReIm(_generate_inner(rng, depth + 1, max_depth, terminal_factory))

    else:
        # conj(e)  (複素共役 — 反転対称性)
        return Conjugate(_generate_inner(rng, depth + 1, max_depth, terminal_factory))


def generate_formula(rng: random.Random) -> ExprNode:
    """フラクタル漸化式 z_{n+1} = f(z, c) の完全な式木を生成する

    トップレベル構造 (5 パターン、均等に近い重み):
      - add_c      (40%): inner(z) + c          … 加算型 (Mandelbrot/Julia 標準)
      - mul_c      (15%): c * inner(z)          … 乗算型
      - product_mix(15%): inner1(z)*inner2(z) + c … 積混合型
      - arg_mix    (15%): inner(z*c)            … 引数混合型
      - func_mul   (15%): c * func(inner(z))    … 関数乗算型
    """
    pattern = rng.choices(
        ["add_c", "mul_c", "product_mix", "arg_mix", "func_mul"],
        weights=[0.40, 0.15, 0.15, 0.15, 0.15],
    )[0]

    if pattern == "add_c":
        inner = _generate_inner(rng, depth=0, max_depth=3)
        return Add(inner, CVar())

    elif pattern == "mul_c":
        inner = _generate_inner(rng, depth=0, max_depth=3)
        return Mul(CVar(), inner)

    elif pattern == "product_mix":
        inner1 = _generate_inner(rng, depth=0, max_depth=2)
        inner2 = _generate_inner(rng, depth=0, max_depth=2)
        return Add(Mul(inner1, inner2), CVar())

    elif pattern == "arg_mix":
        inner = _generate_inner(rng, depth=0, max_depth=3, terminal_factory=ZCProduct)
        return Add(inner, CVar())

    else:  # func_mul
        func = rng.choice(["sin", "cos"])
        inner = _generate_inner(rng, depth=0, max_depth=3)
        return Mul(CVar(), UnaryFunc(func, inner))


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 漸化式ラッパー
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class GeneratedFormula:
    """生成された式木をラップし、iterate() / display_formula() を提供する"""

    def __init__(self, rng: random.Random):
        self.name = "Generated"
        self.expr = generate_formula(rng)

    def iterate(self, z: np.ndarray, c: np.ndarray) -> np.ndarray:
        """z, c に対して 1 ステップの反復を実行する"""
        return self.expr.evaluate(z, c)

    def display_formula(self) -> str:
        """人間可読な式の文字列表現を返す"""
        return self.expr.display()
