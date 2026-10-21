#!/usr/bin/env python3
"""Small stdlib golden checks; run directly, no build or test framework."""
import random
import string

from check_localization import (
    call_findings, catalog_entries, constant, lex, literal, lower_findings,
    placeholders, suspicious,
)


def main():
    golden = [
        ('u"prefix " /* gap */ "suffix"_q', "prefix suffix"),
        (r'u"quote: \" slash: \\ \u0410\U0001F600\n"_q', 'quote: " slash: \\ А😀\n'),
        ('u"joined\\\nline"_q', "joinedline"),
        ('u"joined\\\r\nline"_q', "joinedline"),
        (r'u"\101\x42"_q', "AB"),
        (r'u"\uD83D\uDE00"_q', "😀"),
        ('uR"tag(raw \\ and "quotes"\n)tag"_q', 'raw \\ and "quotes"\n'),
        ('QStringView(u"a" "b")', "ab"),
        ('(u"a"_q)', "a"),
        ('QStringView{}', ""),
    ]
    for source, expected in golden:
        tokens, errors = lex(source)
        assert not errors, (source, errors)
        assert literal(tokens) == expected, (source, literal(tokens), expected)
    for source in (r'u"\uZZZZ"', r'u"\U00110000"', 'u"unterminated', '/* missing'):
        assert lex(source)[1], source
    for source in ('u"a"_q.arg(x)', 'u"a" + u"b"', 'variable'):
        assert literal(lex(source)[0]) is None, source
    assert placeholders('%1 %2 %1 %L1 %n %% %Ln') == {
        '%1': 2, '%2': 1, '%L1': 1, '%n': 1, '%%': 1, '%Ln': 1,
    }
    assert placeholders('%1 %2') == placeholders('%2 %1')
    for changed in ('%1', '%1 %1 %2', '%L1 %2', '%n %2', '%% %2'):
        assert placeholders('%1 %2') != placeholders(changed), changed
    assert placeholders('100% done %foo') == {}
    catalog = '''const Entry kEntries[] = {
        {QStringView(u"prefix " "suffix"), u"перевод"_q},
        {QStringView(u"%1"), u"%1"_q, QStringView(u"button")},
    };'''
    entries, errors = catalog_entries(lex(catalog)[0])
    assert not errors, errors
    assert entries == [('prefix suffix', 'перевод', '', 2), ('%1', '%1', 'button', 3)]
    keys = {(source, context) for source, _, context, _ in entries}
    cases = [
        ('I18n::Text(u"prefix " "suffix"_q).arg(x);', set()),
        ('Tele::I18n::Text(u"%1"_q, u"button");', set()),
        ('I18n::Text(u"prefix " "suffix"_q, u"other");', set()),
        ('I18n::Text(u"prefix " "suffix"_q, {});', set()),
        ('I18n::Text(u"%1"_q);', {'missing-translation'}),
        ('I18n::Text(u"missing"_q);', {'missing-translation'}),
        ('I18n::Text(u"%1"_q.arg(x));', {'formatted-before-translation'}),
        ('I18n::Text(value);', set()),
        ('I18n::Text(u"missing"_q, runtimeContext);', set()),
        ('I18n::Plural(n, u"%1 item", u"%1 items", u"%1 вещь", u"%1 вещи", u"%1 вещей");', set()),
        ('I18n::Plural(n, u"%1 item", u"%1 items", u"%2 вещь", u"%1 вещи", u"%1 вещей");', {'placeholder-multiset'}),
        ('I18n::Plural(n, u"one");', {'plural-arity'}),
        ('Lower(u"missing"_q);', set()),
        ('Other::Text(u"missing"_q);', set()),
        ('// I18n::Text(u"missing"_q);\n/* I18n::Text("missing"); */', set()),
        ('// continued\\\nI18n::Text("missing");\n', set()),
        ('"I18n::Text(\\"missing\\")"; char c = \'"\';', set()),
        ("auto n = 1'000; I18n::Text(u\"prefix \" \"suffix\"_q);", set()),
    ]
    for source, expected in cases:
        tokens, errors = lex(source)
        assert not errors, (source, errors)
        findings, _, _ = call_findings(tokens, keys)
        assert {finding[2] for finding in findings} == expected, (source, findings)
    assert lower_findings(lex('QString Lower(QString x) { I18n::Translate(x, &x); return x; }')[0])
    assert not lower_findings(lex('QString Lower(QString x) { /* I18n::Translate(x); */ return x; }')[0])
    assert constant(lex('const auto kPublicKeyHex = "ab" /* gap */ "cd";')[0], 'kPublicKeyHex') == 'abcd'
    assert suspicious('Русский и English') == []
    assert suspicious('РџСЂРёРІРµС‚')
    assert suspicious('\ufffd')
    assert suspicious('\ud800')
    assert not suspicious('😀\nТекст')
    randomizer = random.Random(20261021)
    fuzz = ['', '\n' * 10000, '.' * 5000, '\x00\x01', '\\' * 5000,
            '/*' * 1000, '"' * 1000, 'u"\\x' + 'f' * 5000 + '"']
    fuzz.extend(''.join(randomizer.choices(string.printable, k=randomizer.randrange(401))) for _ in range(4000))
    for source in fuzz:
        tokens, _ = lex(source)
        literal(tokens)
        placeholders(source)
        suspicious(source)
        catalog_entries(tokens)
        call_findings(tokens, keys)
        lower_findings(tokens)
    print(f'Golden lexer/catalog/call/placeholder checks passed; {len(fuzz)} deterministic fuzz inputs, no crashes.')


if __name__ == '__main__':
    main()
