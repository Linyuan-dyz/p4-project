#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""辅助模块：Level 4 多模态完整性裁决

使用场景：
  - basic.p4 集成 level4_integrity.p4inc；
  - S1 / S2 在汇聚点 clone3 I2E 报文到 CPU，带有 integrity_report 头；
  - 控制器收到 PacketIn 后，从报文中解析出：flow_hash, modal_id, integrity_tag；
  - 本模块聚合多模态上报，对每个 flow_hash 选出“胜出模态”，
    并向表 MyIngress.l4_integrity_winner 下发表项：
        match:  meta.flow_hash == flow_hash
        action: l4_set_winner(winner_modal)
"""

import collections
from typing import Dict, List, Tuple

IntegrityRecord = collections.namedtuple(
    "IntegrityRecord", ["modal_id", "integrity_tag"]
)

class IntegrityAdjudicator:
    def __init__(self, p4info_helper, sw, min_reports_per_flow: int = 2):
        self.p4info_helper = p4info_helper
        self.sw = sw
        self.min_reports_per_flow = min_reports_per_flow
        self._records: Dict[int, List[IntegrityRecord]] = {}
        self._winners: Dict[int, int] = {}

    def parse_packet_in(self, packet_in) -> Tuple[int, int, int]:
        """从 PacketIn 中解析 (flow_hash, modal_id, integrity_tag)。

        具体解析方式取决于你在 basic.p4 中如何把 integrity_report_t
        放到报文里（一般可以用 scapy 定义同样的 header 结构来解析）。

        此处留空，需在 controller.py 中根据实际报文结构自行实现。
        """
        raise NotImplementedError(
            "请在 controller.py 中实现 IntegrityAdjudicator.parse_packet_in()"
        )

    def add_record(self, flow_hash: int, modal_id: int, integrity_tag: int):
        recs = self._records.setdefault(flow_hash, [])
        recs.append(IntegrityRecord(modal_id, integrity_tag))

    def maybe_decide(self, flow_hash: int):
        if flow_hash in self._winners:
            return

        recs = self._records.get(flow_hash, [])
        if len(recs) < self.min_reports_per_flow:
            return

        buckets: Dict[int, List[int]] = {}
        for r in recs:
            buckets.setdefault(r.integrity_tag, []).append(r.modal_id)

        best_tag = None
        best_modals: List[int] = []
        for tag, modals in buckets.items():
            if best_tag is None or len(modals) > len(best_modals):
                best_tag = tag
                best_modals = modals

        winner_modal = min(best_modals)
        self._winners[flow_hash] = winner_modal
        self._install_winner_rule(flow_hash, winner_modal)

    def _install_winner_rule(self, flow_hash: int, winner_modal: int):
        table_name = "MyIngress.l4_integrity_winner"
        action_name = "MyIngress.l4_set_winner"

        table_entry = self.p4info_helper.buildTableEntry(
            table_name=table_name,
            match_fields={
                "meta.flow_hash": flow_hash,
            },
            action_name=action_name,
            action_params={
                "winner_modal": winner_modal,
            },
        )
        self.sw.WriteTableEntry(table_entry)
        print(
            f"[Integrity] Install winner for flow_hash=0x{flow_hash:x}, "
            f"winner_modal={winner_modal}"
        )

