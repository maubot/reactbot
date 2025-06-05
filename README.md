English | [中文](README_ZH.md)

# reactbot
A [maubot](https://github.com/maubot/maubot) that responds to messages based on predefined rules.

## Examples
* [base config](base-config.yaml) contains a cookie reaction for TWIM submissions in [#thisweekinmatrix:matrix.org](https://matrix.to/#/#thisweekinmatrix:matrix.org) and an image response for "alot".
* [samples/jesari.yaml](samples/jesari.yaml) contains a replacement for [jesaribot](https://github.com/maubot/jesaribot).
* [samples/stallman.yaml](samples/stallman.yaml) contains a Stallman interjection bot.
* [samples/random-reaction.yaml](samples/random-reaction.yaml) has an example of a random reaction to matching messages.
* [samples/nitter.yaml](samples/nitter.yaml) has an example of matching tweet links and responding with corresponding nitter.net links.
* [samples/thread.yaml](samples/thread.yaml) has an example of replying in threads.

## Configuration Format
### Templates
Templates contain the actual event type and content to be sent.
* `type` - The Matrix event type to send.
* `content` - The event content. Can be an object or a jinja2 template that generates JSON.
* `variables` - Key-value mapping of variables.

Variables starting with `{{` will be parsed as jinja2 templates and will get the maubot event object in `event`. From v3 onwards, variables are parsed using jinja2's [native types mode](https://jinja.palletsprojects.com/en/3.1.x/nativetypes/), meaning the output can be non-string types.

If the content is a string, it will be parsed as a jinja2 template, and the output will be parsed as JSON. Content jinja2 templates will get `event` like variable templates but will also get all variables.

If the content is an object, the object will be sent as the content. Objects can include variables using custom syntax: all instances of `$${variablename}` will be replaced with the value matching `variablename`. This applies to object keys and values as well as list items. If a key/value/item only contains a variable insertion, the variable can be of any type. If there is other content besides the variable, the variable will be concatenated using `+`, meaning it should be a string.

### Default Flags
Default regular expression flags. Most Python regular expression flags are available. See [documentation](https://docs.python.org/3/library/re.html#re.A).

Most relevant flags:
* `i` / `ignorecase` - Case-insensitive matching.
* `s` / `dotall` - Makes `.` match any character, including newlines.
* `x` / `verbose` - Ignores whitespace and comments in the regex.
* `m` / `multiline` - When specified, `^` and `$` match the start and end of each line, not just the start and end of the whole string.

### Rules
Rules only require `matches` and `template`.
* `rooms` - List of rooms (internal room IDs) the rule applies to. If empty, the rule applies to all rooms the bot is in.
* `not_rooms` - Exclude certain rooms (internal room IDs).
* `users` - List of users the rule applies to. If empty, the rule applies to all users.
* `not_users` - Exclude certain users.
* `matches` - Regular expression or list of regular expressions to match.
* `template` - Name of the template to use.
* `variables` - Key-value mapping to extend or override template variables. Like template variables, values will be parsed as Jinja2 templates.
* `only_text` - Should only respond to text-type messages (including notice-type events)? Defaults to false.
* `not_thread` - Should not respond to messages in threads? Defaults to false.
* `is_reedit` - Should not respond to edits? Defaults to false.

Regular expressions in `matches` can be simple strings containing the pattern or objects containing additional information:
* `pattern` - The regular expression to match.
* `flags` - Regular expression flags (override default flags).
* `raw` - Whether the regular expression should be forced to raw.

If `raw` is `true` or the pattern does not contain special regex characters other than leading `^` and/or trailing `$`, the pattern will be treated as "raw". Raw patterns do not use regular expressions but faster string operators (equals, starts/endswith, contains). Patterns with the `multiline` flag will never be implicitly converted to raw patterns.
