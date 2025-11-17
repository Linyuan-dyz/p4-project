README_LEVEL4
=============

本压缩包提供三个文件：

1. level4_integrity.p4inc
   - 与 basic.p4 同级，编译时由 basic.p4 通过
         #include "level4_integrity.p4inc"
     引入（位置在 control MyIngress 内部）。
   - 提供 4 个动作 / 1 张表：
       * l4_compute_flow_and_payload_hash()
       * l4_clone_to_cpu()
       * l4_set_winner()
       * l4_drop_if_not_winner()
       * 表 MyIngress.l4_integrity_winner

   - 在 MyIngress.apply() 中，推荐在 IPv4 发往主机前插入：

        if (hdr.ipv4.isValid()) {
            l4_compute_flow_and_payload_hash();
            l4_clone_to_cpu();
            l4_integrity_winner.apply();
            l4_drop_if_not_winner();
            // 之后继续 ipv4_lpm / vxlan_lpm 等原有逻辑
        }

2. controller_level4_helper.py
   - 与 controller.py 同级。
   - 在 controller.py 中：

        from controller_level4_helper import IntegrityAdjudicator

     创建对象，例如：

        self.integrity_s2 = IntegrityAdjudicator(p4info_helper, self.switches['s2'])

     在 PacketIn 处理逻辑中：

        flow_hash, modal_id, integrity_tag =             self.integrity_s2.parse_packet_in(pkt_in)
        self.integrity_s2.add_record(flow_hash, modal_id, integrity_tag)
        self.integrity_s2.maybe_decide(flow_hash)

3. README_LEVEL4.txt
   - 即本说明，帮助你把 Level 4 的“数据完整性裁决”接到当前仓库。

注意：模态随机调度（ECMP + multicast 部分）没有强耦合到此补丁，你可以
在现有 IPv4 / IPv6 / Yequdesu / VXLAN 路由基础上，参考课程提供的
负载均衡示例，在 S1 / S2 上额外增加一张哈希表，实现模态的随机选择。

