"""RRF 加权的纯单元测试。

只 import `hybrid_retrieval`：该模块顶层仅加载 numpy，jieba / sentence-transformers
都在函数内懒加载，所以这里**不碰模型、不建索引**，毫秒级跑完。

为什么用合成排名表而不是端到端：线上的 `RAG_W_BM25=2.0 / RAG_W_VECTOR=1.0`
来自 D36 阶段 2 端到端评测（跑一次约 100min），而 RRF 的数学性质（常数缩放不变、
权重与路一一对应、加权能改次序）是确定的，用合成表就能钉死。
"""
import os
import sys

import pytest

# 允许 `python -m pytest` 从任意 cwd 运行（与 tests/unit/test_config.py 同款处理）
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.services.hybrid_retrieval import HybridRetriever

pytestmark = pytest.mark.unit

rrf = HybridRetriever.rrf


def _ranked(ids):
    """把 doc_id 列表转成 RRF 要的排名表。RRF 只取次序，score 被忽略。"""
    return [(doc_id, 1.0) for doc_id in ids]


def _order(ranked):
    return [doc_id for doc_id, _ in ranked]


def _pos(ranked, doc_id):
    return _order(ranked).index(doc_id)


# 两路排名表，部分重叠。融合输入顺序约定为 [vector, bm25]（D36 的「口径」坑）。
VECTOR = _ranked(["v1", "both1", "v2", "both2", "v3", "v4"])
BM25 = _ranked(["both1", "b1", "both2", "b2", "b3", "b4"])


class TestWeightScaleInvariance:
    """RRF 对权重整体缩放不变 —— 所以 `2:1` 与 `20:10` 是同一套配置。"""

    def test_default_equals_explicit_equal_weights(self):
        assert _order(rrf([VECTOR, BM25], k=60)) == _order(
            rrf([VECTOR, BM25], k=60, weights=[1.0, 1.0])
        )

    @pytest.mark.parametrize("scale", [0.25, 0.5, 2.0, 10.0, 100.0])
    def test_equal_weights_scale_does_not_change_order(self, scale):
        base = _order(rrf([VECTOR, BM25], k=60, weights=[1.0, 1.0]))
        assert _order(rrf([VECTOR, BM25], k=60, weights=[scale, scale])) == base

    @pytest.mark.parametrize("scale", [0.2, 0.5, 5.0, 10.0])
    def test_production_ratio_scale_does_not_change_order(self, scale):
        """线上 2:1（bm25 权重是向量的 2 倍）等比缩放后排序必须一致。"""
        base = _order(rrf([VECTOR, BM25], k=5, weights=[1.0, 2.0]))
        scaled = _order(rrf([VECTOR, BM25], k=5, weights=[1.0 * scale, 2.0 * scale]))
        assert scaled == base


class TestWeightedReciprocalRank:
    """逐项钉死公式 `Σ w_i/(k+rank_i)`，同时钉死「权重的第 i 项配第 i 路」。"""

    def test_score_equals_weighted_reciprocal_rank(self):
        list1 = _ranked(["A", "B"])
        list2 = _ranked(["B", "A"])
        out = dict(rrf([list1, list2], k=10, weights=[3.0, 1.0]))
        # A: 第 1 路 rank1，第 2 路 rank2
        assert out["A"] == pytest.approx(3.0 / 11 + 1.0 / 12)
        # B: 第 1 路 rank2，第 2 路 rank1 —— 权重配反了这两个数就会互换
        assert out["B"] == pytest.approx(3.0 / 12 + 1.0 / 11)

    def test_single_list_ranks_by_rank_only(self):
        out = _order(rrf([_ranked(["x", "y", "z"])], k=5, weights=[7.0]))
        assert out == ["x", "y", "z"]

    def test_weights_must_match_ranked_lists(self):
        """长度不匹配必须报错：`zip` 会静默截断，产出「看似正常」的错误排序。"""
        with pytest.raises(ValueError):
            rrf([VECTOR, BM25], k=5, weights=[2.0])


class TestBm25HeavyWeightPromotesBm25Doc:
    """线上配置 `bm25×2` 的实际作用：把只在 bm25 路的文档提到只在 vector 路的文档之前。

    构造（k=5，任一路的分数为 1/(5+rank)）：
      d_vec —— vector 路 rank5，bm25 路**不在表里**  ⇒ 等权 1/10  = 0.1000
      d_bm  —— bm25   路 rank10，vector 路**不在表里** ⇒ 等权 1/15  = 0.0667
    等权时 d_vec 在前；bm25 权重加倍后 d_bm 得 2/15 = 0.1333 > 0.1000，反超。
    """

    VEC_ONLY_TABLE = _ranked(["f1", "f2", "f3", "f4", "d_vec", "f5", "f6", "f7", "f8", "f9"])
    BM_ONLY_TABLE = _ranked(["g1", "g2", "g3", "g4", "g5", "g6", "g7", "g8", "g9", "d_bm"])

    def test_equal_weights_keep_vector_doc_ahead(self):
        out = rrf([self.VEC_ONLY_TABLE, self.BM_ONLY_TABLE], k=5, weights=[1.0, 1.0])
        assert _pos(out, "d_vec") < _pos(out, "d_bm")

    def test_bm25_double_weight_promotes_bm25_doc(self):
        out = rrf([self.VEC_ONLY_TABLE, self.BM_ONLY_TABLE], k=5, weights=[1.0, 2.0])
        assert _pos(out, "d_bm") < _pos(out, "d_vec")

    def test_order_pairs_first_weight_with_first_list(self):
        """权重给反（把 2 给 vector）会得到与上文相反的结果 —— 这就是 D36 记的「口径」坑。"""
        out = rrf([self.VEC_ONLY_TABLE, self.BM_ONLY_TABLE], k=5, weights=[2.0, 1.0])
        assert _pos(out, "d_vec") < _pos(out, "d_bm")
