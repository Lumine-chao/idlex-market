"""基础数据初始化：分类树、敏感词库、管理账号、演示账号与演示商品"""
import asyncio
from .db import SessionLocal, engine, Base
from . import models
from .auth import hash_password
from .sensitive import build_from_words
from sqlalchemy import select

CATEGORIES = [
    ("手机数码", [
        ("手机", ["iPhone", "安卓机型", "折叠屏"]),
        ("平板电脑", ["iPad", "安卓平板"]),
        ("相机", ["单反微单", "卡片机", "拍立得"]),
        ("耳机音响", ["耳机", "音响"]),
    ]),
    ("电脑办公", [
        ("笔记本电脑", ["Windows本", "MacBook", "轻薄本"]),
        ("台式机", ["主机", "显示器"]),
    ]),
    ("服装鞋包", [
        ("女装", ["连衣裙", "外套", "衬衫"]),
        ("男装", ["T恤", "卫衣"]),
        ("鞋靴", ["运动鞋", "休闲鞋"]),
        ("箱包", ["双肩包", "单肩包"]),
    ]),
    ("图书文娱", [
        ("图书", ["小说", "教材", "童书"]),
        ("影音娱乐", ["游戏碟", "音乐"]),
    ]),
    ("母婴玩具", [
        ("母婴", ["推车", "奶瓶"]),
        ("玩具", ["积木", "拼装模型"]),
    ]),
    ("家居日用", [
        ("家具", ["桌椅", "柜子"]),
        ("家居日用", ["灯具", "收纳"]),
    ]),
]

SENSITIVES = ["诈骗", "赌博", "色情", "违禁品", "假货", "办证", "枪支", "私聊微信转账", "刷单返利"]

# 演示商品：(卖家用户名, 标题, 描述, 成色1-4, 价格, 原价倍数, 末级分类名)
# 按标题幂等补齐：新增条目后重跑 seed 即可追加，不会重复插入
DEMO_ITEMS = [
    # 手机数码
    ("xiaozhou", "iPhone 13 128G 国行", "自用一年，电池效率88%，成色不错，无拆修。", 2, 2899.00, 1.6, "iPhone"),
    ("xianzhidaren", "iPad Air 5 64G 紫色", "几乎全新，带上壳和膜，教育优惠入手。", 1, 3399.00, 1.5, "iPad"),
    ("xianzhidaren", "华为 Mate 60 Pro 12+512 雅川青", "自用半年，无磕碰无划痕，原装充电器齐全。", 2, 5299.00, 1.2, "安卓机型"),
    ("zhangshop", "佳能 EOS R50 微单套机 白色", "快门数不到3000，带18-45套头，送相机包。", 1, 4199.00, 1.2, "单反微单"),
    ("zhangshop", "索尼 WH-1000XM4 降噪耳机", "几乎全新，配件齐全，音质很好。", 2, 1299.00, 1.5, "耳机"),
    ("zhangshop", "Bose SoundLink Mini II 蓝牙音箱", "音质很赞，续航正常，外观有轻微使用痕迹。", 3, 599.00, 1.6, "音响"),
    ("xianzhidaren", "小米 智能手环 8", "全新未拆封，买多了一个。", 1, 159.00, 2.0, "手环手表"),
    # 电脑办公
    ("xiaozhou", "MacBook Air M2 13寸 8G+256G", "深空灰，电池循环68次，成色很好，带原装充电线。", 2, 5599.00, 1.3, "MacBook"),
    ("zhangshop", "联想 ThinkPad X1 Carbon 2023", "公司发的用不上，键盘手感好，无维修记录。", 2, 6899.00, 1.4, "轻薄本"),
    ("zhangshop", "戴尔 27寸 4K 显示器", "轻微使用痕迹，无亮点坏点，搬家出。", 3, 999.00, 1.9, "显示器"),
    ("xianzhidaren", "组装台式机 i5-12400F + RTX3060", "自用两年运行稳定，只支持同城自提。", 4, 3299.00, 1.5, "主机"),
    # 服装鞋包
    ("xianzhidaren", "始祖鸟 冲锋衣 黑色 M码", "有使用痕迹但功能完好，防泼水仍不错。", 4, 1200.00, 1.7, "外套"),
    ("xiaozhou", "优衣库 男款 卫衣 灰色 L码", "穿过两次，无起球，洗过一次。", 2, 89.00, 2.0, "卫衣"),
    ("zhangshop", "Nike Air Force 1 白色 42码", "上脚次数不多，鞋底磨损轻微，鞋盒还在。", 3, 399.00, 1.8, "运动鞋"),
    ("xianzhidaren", "无印良品 双肩包 深蓝色", "通勤用了半年，拉链顺滑，无破损。", 3, 168.00, 2.0, "双肩包"),
    # 图书文娱
    ("xiaozhou", "《三体》三部曲 科幻全集", "完整一套三本，保存完好，包邮。", 3, 55.00, 1.0, "小说"),
    ("xiaozhou", "《哈利·波特》全集 中文版 7册", "全套七册，无笔记无划线，书脊完好。", 2, 210.00, 1.6, "小说"),
    ("zhangshop", "塞尔达传说 王国之泪 卡带", "通关出，卡带无划痕，可面交验货。", 2, 245.00, 1.4, "游戏碟"),
    # 母婴玩具
    ("xiaozhou", "乐高 积木 机械组 跑车", "拼过一次，拆装完整，缺一小件零件。", 3, 680.00, 1.3, "积木"),
    ("xianzhidaren", "好孩子 婴儿推车 可折叠", "宝宝大了用不上，折叠收纳方便，已清洁消毒。", 3, 480.00, 1.7, "推车"),
    ("xiaozhou", "万代 高达 拼装模型 RG 独角兽", "拼装完成品，已上水贴，摆柜展示。", 3, 165.00, 1.4, "拼装模型"),
    # 家居日用
    ("zhangshop", "宜家 实木书桌 120x60cm", "搬家出，桌面无划痕，需自提。", 3, 350.00, 1.9, "桌椅"),
    ("xianzhidaren", "小米 智能台灯 Pro", "无频闪，可调色温，功能一切正常。", 2, 199.00, 1.6, "灯具"),
    ("xiaozhou", "透明收纳箱 大号 3个装", "买多了，全新未使用，可叠放。", 1, 60.00, 1.8, "收纳"),
]


def build_categories() -> list[models.Category]:
    """生成三级分类树并返回（用显式 id 便于父子引用）。"""
    all_rows = []
    seed = 100
    for lv1 in CATEGORIES:
        l1_id = seed
        seed += 1
        all_rows.append(models.Category(id=l1_id, name=lv1[0], parent_id=None, level=1, sort=l1_id))
        for lv2 in lv1[1]:
            l2_id = seed
            seed += 1
            all_rows.append(models.Category(id=l2_id, name=lv2[0], parent_id=l1_id, level=2, sort=l2_id))
            for leaf_name in lv2[1]:
                l3_id = seed
                seed += 1
                all_rows.append(models.Category(id=l3_id, name=leaf_name, parent_id=l2_id,
                                                level=3, sort=l3_id))
    # 手机数码下补充「智能穿戴」：用显式 id 追加，避免打乱上面按顺序分配的 id
    all_rows.append(models.Category(id=159, name="智能穿戴", parent_id=100, level=2, sort=159))
    all_rows.append(models.Category(id=160, name="手环手表", parent_id=159, level=3, sort=160))
    return all_rows


# 后加的列：{表名: [(列名, 列定义)]}
_ADDED_COLUMNS = {
    "conversations": [
        ("buyer_read_at", "DATETIME"),
        ("seller_read_at", "DATETIME"),
    ],
}


def _migrate_columns(conn):
    from sqlalchemy import inspect, text
    insp = inspect(conn)
    existing_tables = set(insp.get_table_names())
    for table, columns in _ADDED_COLUMNS.items():
        if table not in existing_tables:
            continue
        have = {c["name"] for c in insp.get_columns(table)}
        for name, ddl in columns:
            if name not in have:
                conn.execute(text(f'ALTER TABLE "{table}" ADD COLUMN "{name}" {ddl}'))


async def seed_demo():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        # 轻量迁移：为既有 SQLite 库补齐后加的列（create_all 不会改已存在的表）
        await conn.run_sync(_migrate_columns)

    async with SessionLocal() as db:
        cnt = (await db.execute(select(models.Category))).scalars().all()
        if not cnt:
            for c in build_categories():
                db.add(c)
            await db.flush()

        wcnt = (await db.execute(select(models.SensitiveWord))).scalars().all()
        if not wcnt:
            for w in SENSITIVES:
                db.add(models.SensitiveWord(word=w, level="BLOCK", status=1))
            await db.flush()

        adm = (await db.execute(select(models.AdminUser))).scalars().first()
        if not adm:
            db.add(models.AdminUser(username="admin", password_hash=hash_password("Admin123"),
                                    role="ADMIN", status=1))

        users = (await db.execute(select(models.User))).scalars().all()
        if not users:
            db.add_all([
                models.User(username="xianzhidaren", phone="13800138000",
                            password_hash=hash_password("Abc12345"),
                            security_question="您最爱的食物是？", security_answer=hash_password("火锅"),
                            city="深圳", credit_level=5, status=1),
                models.User(username="xiaozhou", phone="13900139000",
                            password_hash=hash_password("Abc12345"),
                            security_question="您的小学名称是？", security_answer=hash_password("实验小学"),
                            city="杭州", credit_level=4, status=1),
                models.User(username="zhangshop", phone="13700137000",
                            password_hash=hash_password("Abc12345"),
                            security_question="您的出生城市是？", security_answer=hash_password("上海"),
                            city="上海", credit_level=3, status=1),
            ])
            await db.flush()

        # 演示商品：按标题幂等补齐，便于后续继续追加
        sellers = {u.username: u for u in
                   (await db.execute(select(models.User))).scalars().all()}
        leaves = (await db.execute(
            select(models.Category).where(models.Category.level == 3))).scalars().all()
        leaf_id_by_name = {c.name: c.id for c in leaves}
        existing_titles = set((await db.execute(select(models.Item.title))).scalars().all())
        for username, title, desc, cond, price, ratio, leaf_name in DEMO_ITEMS:
            seller = sellers.get(username)
            if not seller or title in existing_titles:
                continue
            it = models.Item(seller_id=seller.id, title=title, description=desc,
                             category_id=leaf_id_by_name[leaf_name], condition_level=cond,
                             price=price, origin_price=round(price * ratio, 2),
                             stock=1, city=seller.city, trade_type=1, freight_payer=1,
                             freight=0, status=3)
            db.add(it)
            await db.flush()
            for j in range(3):
                db.add(models.ItemImage(item_id=it.id, url="", sort=j, audit_status=2))
        await db.commit()

    async with SessionLocal() as db:
        words = (await db.execute(
            select(models.SensitiveWord).where(models.SensitiveWord.status == 1)
        )).scalars().all()
        build_from_words([w.word for w in words])


if __name__ == "__main__":
    asyncio.run(seed_demo())
    print("seed done")