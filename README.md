# reactbot
A [maubot](https://github.com/maubot/maubot) that responds to messages that match predefined rules.

## Samples
* The [base config](base-config.yaml) contains a cookie reaction for TWIM submissions
  in [#thisweekinmatrix:matrix.org](https://matrix.to/#/#thisweekinmatrix:matrix.org)
  and an image response for "alot".
* [samples/jesari.yaml](samples/jesari.yaml) contains a replacement for [jesaribot](https://github.com/maubot/jesaribot).
* [samples/stallman.yaml](samples/stallman.yaml) contains a Stallman interject bot.
* [samples/random-reaction.yaml](samples/random-reaction.yaml) has an example of
  a randomized reaction to matching messages.
* [samples/nitter.yaml](samples/nitter.yaml) has an example of matching tweet links
  and responding with a corresponding nitter.net link.
* [samples/thread.yaml](samples/thread.yaml) has an example of replying in a thread.

## Config format
### Templates
Templates contain the actual event type and content to be sent.
* `type` - The Matrix event type to send
* `content` - The event content. Either an object or jinja2 template that produces JSON.
* `variables` - A key-value map of variables.

Variables that start with `{{` are parsed as jinja2 templates and get the
maubot event object in `event`. As of v3, variables are parsed using jinja2's
[native types mode](https://jinja.palletsprojects.com/en/3.1.x/nativetypes/),
which means the output can be a non-string type.

If the content is a string, it'll be parsed as a jinja2 template and the output
will be parsed as JSON. The content jinja2 template will get `event` just like
variable templates, but it will also get all of the variables.

If the content is an object, that object is what will be sent as the content.
The object can contain variables using a custom syntax: All instances of
`$${variablename}` will be replaced with the value matching `variablename`.
This works in object keys and values and list items. If a key/value/item only
consists of a variable insertion, the variable may be of any type. If there's
something else than the variable, the variable will be concatenated using `+`,
which means it should be a string.

### Default flags
Default regex flags. Most Python regex flags are available.
See [docs](https://docs.python.org/3/library/re.html#re.A).

Most relevant flags:
* `i` / `ignorecase` - Case-insensitive matching.
* `s` / `dotall` - Make `.` match any character at all, including newline.
* `x` / `verbose` - Ignore comments and whitespace in regex.
* `m` / `multiline` - When specified, `^` and `$` match the start and end of
                      line respectively instead of start and end of whole string.

### Rules
Rules have five fields. Only `matches` and `template` are required.
* `rooms` - The list of rooms where the rule should apply.
            If empty, the rule will apply to all rooms the bot is in.
* `matches` - The regex or list of regexes to match.
* `template` - The name of the template to use.
* `variables` - A key-value map of variables to extend or override template variables.
                Like with template variables, the values are parsed as Jinja2 templates.

The regex(es) in `matches` can either be simple strings containing the pattern,
or objects containing additional info:
* `pattern` - The regex to match.
* `flags` - Regex flags (replaces default flags).
* `raw` - Whether or not the regex should be forced to be raw.

If `raw` is `true` OR the pattern contains no special regex characters other
than `^` at the start and/or `$` at the end, the pattern will be considered
"raw". Raw patterns don't use regex, but instead use faster string operators
(equality, starts/endwith, contains). Patterns with the `multiline` flag will
never be converted into raw patterns implicitly.
