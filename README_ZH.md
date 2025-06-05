[English](README.md) | 中文

# reactbot
一个[maubot](https://github.com/maubot/maubot) ，根据预定义规则响应消息。

## 示例
* [base config](base-config.yaml) 包含一个针对 [#thisweekinmatrix:matrix.org](https://matrix.to/#/#thisweekinmatrix:matrix.org) 中 TWIM 提交的 cookie 反应和一个针对 "alot" 的图片响应。
* [samples/jesari.yaml](samples/jesari.yaml) 包含一个 [jesaribot](https://github.com/maubot/jesaribot) 的替代品。
* [samples/stallman.yaml](samples/stallman.yaml) 包含一个 Stallman 插话机器人。
* [samples/random-reaction.yaml](samples/random-reaction.yaml) 有一个对匹配消息进行随机反应的示例。
* [samples/nitter.yaml](samples/nitter.yaml) 有一个匹配推文链接并回应相应 nitter.net 链接的示例。
* [samples/thread.yaml](samples/thread.yaml) 有一个在线程中回复的示例。

## 配置格式
### Templates
模板包含要发送的实际事件类型和内容。
* `type` - 要发送的 Matrix 事件类型
* `content` - 事件内容。可以是对象或生成 JSON 的 jinja2 模板。
* `variables` - 变量的键值对映射。

以 `{{` 开头的变量将被解析为 jinja2 模板，并在 `event` 中获取 maubot 事件对象。从 v3 开始，变量使用 jinja2 的[原生类型模式](https://jinja.palletsprojects.com/en/3.1.x/nativetypes/)进行解析 ，这意味着输出可以是非字符串类型。

如果内容是字符串，它将被解析为 jinja2 模板，输出将被解析为 JSON。内容 jinja2 模板将像变量模板一样获取 `event`，但它也将获取所有变量。

如果内容是对象，该对象将作为内容发送。对象可以使用自定义语法包含变量：所有 `$${variablename}` 实例将被替换为与 `variablename` 匹配的值。这适用于对象键和值以及列表项。如果键/值/项仅包含变量插入，则变量可以是任何类型。如果除了变量还有其他内容，变量将使用 `+` 连接，这意味着它应该是字符串。

### Default flags
默认正则表达式标志。大多数 Python 正则表达式标志可用。参见[文档](https://docs.python.org/3/library/re.html#re.A) 。

最相关的标志：
* `i` / `ignorecase` - 不区分大小写匹配。
* `s` / `dotall` - 使 `.` 匹配任何字符，包括换行符。
* `x` / `verbose` - 忽略正则表达式中的注释和空白。
* `m` / `multiline` - 指定时，`^` 和 `$` 分别匹配行的开始和结束，而不是整个字符串的开始和结束。

### Rules
规则只有 `matches` 和 `template` 是必需的。
* `rooms` - 规则适用的房间列表（内部房间ID）。如果为空，规则将适用于机器人所在的所有房间。
* `not_rooms` - 排除某些房间（内部房间ID）。
* `users` - 规则适用的用户列表。如果为空，规则将适用于所有用户。
* `not_users` - 排除某些用户。
* `matches` - 要匹配的正则表达式或正则表达式列表。
* `template` - 要使用的模板名称。
* `variables` - 扩展或覆盖模板变量的键值对映射。与模板变量一样，值将被解析为 Jinja2 模板。
* `only_text` - 是否只回应文本类消息（包括通知类型的事件）？默认为false
* `not_thread` - 是否不回应线程内的消息？默认为false
* `is_reedit` - 否不回应编辑？默认为false

`matches` 中的正则表达式可以是包含模式的简单字符串，也可以是包含附加信息的对象：
* `pattern` - 要匹配的正则表达式。
* `flags` - 正则表达式标志（替换默认标志）。
* `raw` - 正则表达式是否应被强制为原始。

如果 `raw` 为 `true` 或模式不包含除开头的 `^` 和/或结尾的 `$` 之外的特殊正则表达式字符，则模式将被视为“原始”。原始模式不使用正则表达式，而是使用更快的字符串操作符（相等、starts/endwith、contains）。带有 `multiline` 标志的模式将永远不会被隐式转换为原始模式。
