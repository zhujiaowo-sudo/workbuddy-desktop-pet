# 稳定分层版1.4.0

原角色作者Buddy娘，CC-BY-4.0。使用内置imagegen生成[分层源图](rig-kit-v1.4.0.png)，无CLI/API回退。初稿存在手臂残留及部件不一致，未用作最终素材；最终修订移除基础人物左侧可见手臂，以同一基础身体配准部件。source PNG透明区域可带隐藏RGB，程序只按alpha读取。

源图上方约66%为三个同身体、不同眼睛的基准，底部为上臂/前臂/手套。`rig_export.py`固定身体、腿、头型和嘴，只切换双眼面板；手臂按基础人物袖宽及肩点统一配准，使用固定长度、固定宽度、关节旋转构建16个真实姿势。上臂在身体后，前臂/手套在前，路径避开双眼；每帧从同一身体重新合成，不能保留旧手臂或把不同整个人物图片叠加。

idle为16帧APNG，12帧睁眼停留后以80ms半闭/闭眼/半睁，完整周期约2.84秒；挠头16帧×100ms，非循环。APNG以SOURCE绘制、交替disposal保留相同停留帧，解码后像素必须与生成帧完全相同。播放器直接显示实际帧，取消整幅图交叉淡化。

质量检查：跨idle/scratch比较腿部、头顶轮廓、嘴部固定区域；眼区不可被抬手遮住；手套独立白色连通区域尺寸与另一只手对照。输出每帧/循环，再对原生150%窗口连续播放两轮、每40ms采样；不能只看几个关键帧。`tools/audit_animations.py`可复验完整包。

## 初始分层提示词

```text
Create ONE transparent 3-column x 2-row PRODUCTION LAYER KIT for rigging this EXACT mint-haired chibi girl. This is NOT an animation of different full-body poses. Preserve identity/outfit: emerald eyes, white cat-ear helmet/headphones, mint bob, white/mint belted tunic skirt, dark green leggings, mint-white boots. All cells clean transparent background with 12% margin. No grid/text/ground shadow. TOP ROW three identical full-body bases: girl front facing, fixed head/body/waist/legs/feet, left arm (VIEWER'S RIGHT) relaxed at side; her RIGHT arm (VIEWER'S LEFT) COMPLETELY HIDDEN BEHIND HER BACK so no sleeve or glove protrudes at viewer left, but keep shoulder and torso intact. Top-left eyes open; top-middle eyes HALF closed; top-right eyes fully closed with a soft smile. Other geometry must be pixel-consistent, no head tilt or change in body width/leg length. Bottom-left: ONLY one separate straight upper-arm white/mint sleeve piece, vertical pointing DOWN, rounded upper shoulder end at top, elbow end bottom; no body/head/hand. Bottom-middle: ONLY one separate straight forearm sleeve, vertical DOWN, elbow top, mint wrist cuff bottom; no torso/head/hand. Bottom-right: ONLY one separate rounded white mitten GLOVE, wrist opening at top, fingers pointing DOWN, no arm/body/head. Sleeve and glove pieces should be large and legible in their own cells, matching the character illustration linework and shading, ready to rotate as rigid bones without morphing. No duplicate or extra figures in bottom cells. The three top bases need exactly one visible arm and glove (viewer right). The hidden arm will be reattached from bottom parts by software. Genuine transparent alpha, opaque character interiors, original simple pastel look.
```

## 最终修订提示词

```text
Correct this rig layer kit, preserve the girl identity, scale, eye variants and 3x2 layout. Critical top-row correction: REMOVE the entire arm on the VIEWER'S LEFT from all three girls. That means remove the curved white sleeve currently visible between the left torso edge and empty space. Do NOT draw that arm behind her back or leave a shoulder oval. The torso on viewer-left should have a clean continuous side outline from the armpit just below the collar down to the belt/skirt. It is an intentionally ARM-LESS base on that side, ready for a separate arm layer. Keep the viewer-right arm relaxed, both legs and head intact and identical in all three bases. Top-left open eyes, top-middle half-closed, top-right closed. Bottom-left redraw as a plain WHITE short upper-arm sleeve segment, straight vertical DOWN, simple narrow capsule, gently rounded at BOTH ends, NO green cuff, NO shoulder pad, NO ball joint, NO circular cap protrusion. Bottom-middle a matching narrow WHITE forearm segment vertical DOWN with a small mint cuff only at lower wrist, rounded elbow top, no flared shape. Bottom-right same white mitten glove and mint cuff, wrist top pointing down. These separate pieces should match the width of the attached other arm; no giant shoulder pads. Empty genuinely transparent background, no grey/green haze, no floor or shadows or labels, opaque character interiors. Preserve exact outfit, face and stable legs. Leave generous space between top full bodies and bottom parts; no clipping.
```
