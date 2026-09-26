"""统一业务错误码与中文提示语（与需求/架构文档一致）。
错误码分段：1xxx 账号、2xxx 商品、3xxx 检索、4xxx 消息、5xxx 订单、6xxx 评价举报、9xxx 系统。
"""
from typing import Optional


class BizError(Exception):
    def __init__(self, code: int, message: str, data=None, http_status: int = 200):
        self.code = code
        self.message = message
        self.data = data
        self.http_status = http_status
        super().__init__(message)


class ErrorCodes:
    # 通用
    PARAM_INVALID = 9001
    UNAUTHORIZED = 401
    FORBIDDEN = 403
    NOT_FOUND = 404
    RATE_LIMITED = 429
    SYSTEM_BUSY = 9999

    # 账号 1xxx
    PHONE_INVALID = 1001
    SMS_CODE_INVALID = 1002
    PASSWORD_FORMAT_INVALID = 1004
    PASSWORD_EQUALS_PHONE = 1005
    PASSWORD_WEAK_SEQUENCE = 1006
    PHONE_REGISTERED = 1007
    USERNAME_INVALID = 1011
    USERNAME_REGISTERED = 1012
    SECURITY_INVALID = 1013
    SECURITY_WRONG = 1014
    LOGIN_FAILED = 1101
    ACCOUNT_LOCKED = 1102
    OLD_PASSWORD_EQUALS = 1103
    ACCOUNT_BANNED = 1104
    PUBLISH_BANNED = 1105
    ADDRESS_LIMIT = 1201
    ADDRESS_MISSING_FIELDS = 1202
    ACCOUNT_ACTIVE_ORDERS = 1203
    SMS_TOO_FREQUENT = 1301
    SMS_DAY_LIMIT = 1302
    PASSWORD_RESET_SAME = 1350

    # 商品 2xxx
    TITLE_LENGTH = 2001
    DESC_LENGTH = 2002
    PRICE_INVALID = 2003
    IMAGE_COUNT = 2004
    IMAGE_FORMAT = 2005
    SENSITIVE_CONTENT = 2006
    ITEM_HAS_ORDERS = 2007
    ITEM_NOT_FOUND = 2008
    ITEM_STATUS_FORBIDDEN = 2009
    STOCK_INVALID = 2010
    CATEGORY_INVALID = 2011
    IMAGE_TOO_LARGE = 2012

    # 检索 3xxx
    KEYWORD_TOO_LONG = 3001
    PRICE_RANGE_INVALID = 3002
    NO_RESULT = 3003

    # 消息 4xxx
    MESSAGE_TOO_LONG = 4001
    MESSAGE_SENSITIVE = 4002
    MESSAGE_TOO_FREQUENT = 4003
    MESSAGE_RECALL_EXPIRED = 4004
    CONVERSATION_NOT_FOUND = 4101

    # 订单 5xxx
    ITEM_SOLD_OUT = 5001
    STOCK_NOT_ENOUGH = 5002
    ADDRESS_REQUIRED = 5003
    PRICE_CARD_INVALID = 5004
    ORDER_EXPIRED = 5005
    ORDER_STATE_FORBIDDEN = 5006
    ORDER_CONFIRM_FORBIDDEN = 5007
    ORDER_NOT_FOUND = 5008
    ORDER_NOT_YOURS = 5009
    ORDER_NO_IMMUTABLE = 5010
    PRICE_CARD_EXPIRED = 5011
    ORDER_DELETE_FORBIDDEN = 5012

    # 评价举报 6xxx
    REVIEW_WINDOW_CLOSED = 6001
    REVIEW_ONLY_ONCE = 6002
    REVIEW_EDIT_LIMIT = 6003
    REPORT_TYPE_REQUIRED = 6101

    # 管理端 7xxx
    ADMIN_REASON_REQUIRED = 7001
    ADMIN_USER_NOT_FOUND = 7002


# ---------- 统一提示文案（供接口直接引用） ----------
MSG = {
    "phone.invalid": "请输入正确的手机号",
    "sms.code.invalid": "验证码错误或已失效",
    "sms.too.frequent": "请求过于频繁，请60秒后重试",
    "password.format": "密码为8～20位，且需同时包含字母与数字",
    "password.equals.account": "密码不能与用户名相同",
    "password.weak": "密码不能为连续或重复字符，请重新设置",
    "username.invalid": "用户名以字母开头，由3～32位字母/数字/下划线组成",
    "username.registered": "该用户名已被注册，换个试试",
    "security.invalid": "请选择密保问题并填写2～50位的答案",
    "security.wrong": "密保答案不正确，无法找回密码",
    "phone.registered": "该手机号已注册，请直接登录",
    "login.failed": "用户名或密码错误，请重试",
    "login.locked": "密码错误次数过多，账号已锁定，请{minutes}分钟后重试",
    "account.banned": "账号已被平台封禁，无法登录",
    "publish.banned": "账号已被平台限制发布商品",
    "reset.same": "新密码不能与当前密码相同",
    "address.limit": "收货地址最多20个",
    "address.missing": "收货人、手机号与详细地址不能为空",
    "account.active.orders": "存在进行中的订单，暂不支持注销",
    "title.length": "标题长度为5～50个字符",
    "desc.length": "描述长度为10～2000个字符",
    "price.invalid": "请输入正确的价格",
    "image.count": "最多上传9张图片",
    "image.format": "最多上传9张图片，仅支持jpg/png/webp格式",
    "image.upload.format": "仅支持 jpg/png/webp 格式的图片，请更换后重试",
    "image.upload.size": "图片大小不能超过 10MB，请压缩后重试",
    "sensitive": "内容包含违规信息，请修改后重新发布",
    "item.has.orders": "该商品有进行中的订单，请先处理完订单后再删除",
    "item.not.found": "商品不存在或已下架",
    "item.status.forbidden": "当前商品状态不允许该操作",
    "item.audit.required": "商品需通过平台审核后才能上架",
    "stock.invalid": "库存数量不正确",
    "category.invalid": "请选择正确的商品分类",
    "keyword.long": "关键词过长，请精简后重试",
    "price.range": "价格区间不正确，请重新输入",
    "no.result": "没有找到相关商品，试试减少筛选条件或更换关键词",
    "message.long": "消息内容过长",
    "message.sensitive": "消息包含违规内容，请修改后重新发送",
    "message.frequent": "操作过于频繁，请稍后再试",
    "message.recall.expired": "消息已超过2分钟，无法撤回",
    "conversation.not.found": "会话不存在",
    "order.sold.out": "该商品已售出，去看看其他商品吧",
    "order.stock": "库存不足，当前仅剩{stock}件",
    "order.address": "请选择收货地址",
    "price.card.invalid": "改价已失效，请重新与卖家确认价格",
    "order.expired": "订单已超时关闭，请重新下单",
    "order.state": "订单状态不允许该操作",
    "order.confirm": "该订单不支持确认收货",
    "order.not.found": "订单不存在",
    "order.not.yours": "订单不存在",
    "order.no.immutable": "订单号不可修改",
    "order.delete.forbidden": "该订单仍在进行中，请先完成或取消后再删除",
    "order.deleted": "订单记录已删除，该记录无法恢复",
    "review.window": "订单完成后30天内可评价，当前已超期",
    "review.once": "评价仅可提交一次",
    "review.edit": "评价仅可修改一次",
    "report.type": "请选择举报类型",
    "admin.reason": "请填写处置原因",
    "admin.user.not.found": "用户不存在",
    "unauthorized": "请先登录",
    "forbidden": "没有权限执行该操作",
    "system.busy": "服务繁忙，请稍后再试",
}


def error(code: int, key: str, **fmt) -> BizError:
    msg = MSG.get(key, "业务处理失败")
    if fmt:
        try:
            msg = msg.format(**fmt)
        except Exception:
            pass
    return BizError(code, msg)