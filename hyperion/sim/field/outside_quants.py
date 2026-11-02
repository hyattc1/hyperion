# Origin: the climb's outside field (docs/drills/field/outside_quants.md is the builder's log). A fresh coding agent,
# playing two quant interns (import-time push/fold equilibria by fictitious play, exact ICM, a Monte Carlo postflop),
# built it in one hour from T0 against the red-team brief and kit, with no access to this repository; frozen at md5
# 27d9b2cb8a03c9e2ae65260b2a9c0b7b (its FROZEN.md5) and copied here unchanged apart from this header. The archive is docs/drills/field/outside_quants_bot.py.
# Played through hyperion.sim.bestiary.Outside*Bot (registry name `out_quants`); a judge-like field, never tuned on.
# Do not edit; a new bot is a new file.
"""rival_bot - quants team.
Import-time tables: 169x169 preflop all-in equity matrix (offline Monte Carlo, embedded),
push/fold equilibria by fictitious play (offline, embedded), prefix sums for equity-vs-top-x%.
Decisions: exact Malmuth-Harville ICM (closed form for the 10/7/5/4/3/2/1/0 table) for all-in
spots, push/fold when short, simple ranges when deep, postflop time-boxed Monte Carlo equity vs
modelled ranges with pot odds. Standard library only."""
import random, base64
from time import perf_counter
from bisect import bisect_left
try:
    from kit import Agent
except Exception:  # pragma: no cover
    class Agent(object):
        pass


# ---------------------------------------------------------------- evaluator
POP = [bin(m).count('1') for m in range(8192)]
STR = [0] * 8192
TOP5 = [0] * 8192
for _m in range(8192):
    _h = 0
    for _hi in range(12, 3, -1):
        _need = 0x1F << (_hi - 4)
        if _m & _need == _need:
            _h = _hi
            break
    if not _h and (_m & 0x100F) == 0x100F:
        _h = 3
    STR[_m] = _h
    _v = 0; _k = 0
    for _r in range(12, -1, -1):
        if _m >> _r & 1:
            _v = (_v << 4) | _r; _k += 1
            if _k == 5:
                break
    TOP5[_m] = _v << (4 * (5 - _k)) if _k < 5 else _v
for _m in range(8192):
    if STR[_m]:
        STR[_m] = STR[_m] << 16


def evaluate(cards):
    cnt = [0] * 13
    s0 = s1 = s2 = s3 = 0
    for c in cards:
        r = c >> 2
        cnt[r] += 1
        s = c & 3
        if s == 0: s0 |= 1 << r
        elif s == 1: s1 |= 1 << r
        elif s == 2: s2 |= 1 << r
        else: s3 |= 1 << r
    for sm in (s0, s1, s2, s3):
        if POP[sm] >= 5:
            sf = STR[sm]
            if sf:
                return 0x800000 | sf
            return 0x500000 | TOP5[sm]
    mask = s0 | s1 | s2 | s3
    q = -1; t1 = -1; t2 = -1; p1 = -1; p2 = -1; p3 = -1; sg = []
    for r in range(12, -1, -1):
        c = cnt[r]
        if c:
            if c == 1: sg.append(r)
            elif c == 2:
                if p1 < 0: p1 = r
                elif p2 < 0: p2 = r
                elif p3 < 0: p3 = r
            elif c == 3:
                if t1 < 0: t1 = r
                else: t2 = r
            else: q = r
    if q >= 0:
        k = -1
        for r in range(12, -1, -1):
            if cnt[r] and r != q:
                k = r; break
        return 0x700000 | q << 16 | k << 12
    if t1 >= 0 and (t2 >= 0 or p1 >= 0):
        pr = t2 if t2 > p1 else p1
        return 0x600000 | t1 << 16 | pr << 12
    st = STR[mask]
    if st:
        return 0x400000 | st
    if t1 >= 0:
        return 0x300000 | t1 << 16 | sg[0] << 12 | sg[1] << 8
    if p2 >= 0:
        k = sg[0] if sg else -1
        if p3 > k: k = p3
        return 0x200000 | p1 << 16 | p2 << 12 | k << 8
    if p1 >= 0:
        return 0x100000 | p1 << 16 | sg[0] << 12 | sg[1] << 8 | sg[2] << 4
    return sg[0] << 16 | sg[1] << 12 | sg[2] << 8 | sg[3] << 4 | sg[4]


def cls_of(c1, c2):
    r1, r2 = c1 >> 2, c2 >> 2
    if r1 < r2: r1, r2 = r2, r1
    if r1 == r2: return r1 * 13 + r1
    if (c1 & 3) == (c2 & 3): return r1 * 13 + r2   # suited: row hi, col lo
    return r2 * 13 + r1                           # offsuit: row lo, col hi

# ---------------------------------------------------------------- embedded offline tables
_EQB64 = (
    "f6mqpqqnqqmsq6qpp5w0jYeJg4qHhYeKioKfgSyDgoiFhYODgoyHnXtzLH+DgIOLhIiHhZ+BeXkxfoCAg4SIh4OjgH5/eSt9"
    "gnuFhoWJpIKBfXt2Lnl/f4KKiJ+CgYF3dnktf3uFhYWegoGDfXh6eC99fYOAn4J9f4N7fHt6L36DiKGEh4KAfHh5dnwxhoOj"
    "hIKEgH9/fXl5dyqBm31+foCDfn56gHmDL1Z/eWdfWVNQS0RLQUJ5G3VhW1BVTUtCRUA8cWshYGNiVVdbWVlZTmFdXB1bWllW"
    "V1hUUVBZWFtZJF1aV1ReWVdXVVZWWU0mT1ZXWllWWFFMWFROTyVVVlVXWFhOTllMVFJPIVVQVlNZR0NTWFBTUlAlV1BaW0RI"
    "U1FOVVJQTyNUU1Y/QU9YWFFWUE9RJFtYP0ZTUVBTVFBLT1UkVD08TlJVUVdQUE9UVCJVhoBnZFVZT0xNSEpCgk11b29kZWJk"
    "Z2VhXXlwG2FaUFBOUEdFQjpmb1gdXl9bWVVZVldRWWVbViVbWVlXW1JVVlNjTlxXIFxWVVJVVVRTX01XVVQpVVRVWlpVTVlN"
    "WldWUSRSUVdTVkZfRFdVUlVTJlpXVlhFWUFTWFFQU08jV1lRRlxEVVJYVFBXUCZVV0deRFJTUlZQVVBaKFg+WTdSWE5YU1JU"
    "VVgiWZiYfl9dUk1SUEpKRJBMenVoZ2pjYGNkYV6SfUp1aGJjY2JgXV5ienJuG1pQUE1HQ0Y/P1pmYlgiXFZZWFdYVFdWY15P"
    "VyVbVlxZW1lVUmFmSlZYKVRVWFhYXE1dYUlVUlglV1hVWFdJYllJTFJXTCRUUlJUR11cQVFSVFRTI1pbVEdcWkJVU1hSUVUn"
    "YVJBX1xGU1JSVldWUChaPVpUOVFSWFVVV1RYIlWgm6B/VlFOTkhFSkGXSoWAdmZkWV9iXWJal3xGhnNgYWJfWltdW5eDeEdp"
    "XVpcX1hYW1h8bm1jFUlMSUI/RTw6VVlXWkgiU05VV1ZTU05eXldFUCJLUVNZWFBJWFZcP05LIVZQUlRZRVhgU0JPTUsjUlBQ"
    "U0tfWFRBTk5OTCFST1tDVlZXQVRQVFBUJltTQ11WXDlPVUxTVFAkWTxXVlI8UUxQTVBUUyFYpqqiqX9KREdDQEFAm06MhYx1"
    "YFlaX1xbVpyDTYuDcVtfY19eXVeagHtLg2tcWVlZWldXoYJ/fUxjVVdXXltkW3pwaWVbEUhDPzw9ODlGW1tQWD4eTUpLU1JT"
    "RFtaVVQ8SB1FSVFPUEBYV1JUP0xIG1BOTlRDWFVXVTVPTEohU1lYQFdVUVY5SUtOTB9RUj9WU1lUN1NNS1BIHlI7VVRWVTlN"
    "SkxOUUwhVaymra61f0VFQkJCQKBKjY+SmnZgYWFlXlyjgEmOkIl2Xl5dXVxdpYKCR4eKaWNWXWBbXJ+IgoBHgWVaWl1dWWGq"
    "joyDfEdbVVhbXF9beHVwYmNUEEE+QT09OEdYW1BTUEIfTU5MTk1EVlZWV1NCSh9QTVZQR1tVWlVTPlBMHVJOUz1YUFZYWTtQ"
    "SEgeVFA7V1JWUlo+TkpNUB9SQ1tWU1RXOlNMVE1MHlavsLKxu7qAQERDP0OlVpOPk5iaeVxdWFxcqIZQhZCRkHVeXF5dWaKB"
    "g06MiY1uWVlgWFukiol+TIqPZFtXWldbr4mHhn5JiVhXY1dbWKuMjYeEhURPV1pcXFp5cm9oYlNIE0M+Pjs7QldcV1ZUUD8c"
    "Sk9PTj9bWFVVU1E9SSBSTVc+V1lYU1VXQEhHHU1UQlpfV1lZWTlOTEshU0VTU1laWVc2TUtKTB5TtLOtsbi6v39FRENBq1KX"
    "jpKWmZh4X1liXaaJTpKTjZiXcl5bWVajhYRTkIuSlmxdWl9eqIiKhkuLio1kW1paXauNho2ES4iLXFhdXlqwlIuKhoFLj1ZV"
    "WlpdrY+OiY2MhENJVlZcXXhvb2tfVE1IED43Ozw9VVVWXldOUD0bTEhUP1RWU1VbVlQ6RR1JUT1XVlxVVVlXOEtNH1M/VlJU"
    "VVRZVzhMS04hVLuyr7e8vbu6gD88PadTjo+YlJKbm3pUXlyogk6Mjo+Zl5d1W1xZroWCSoqIko+Yb1taV6+Kh39OiZKOl2pb"
    "WF6uj4iFgE2Jko1XXFdisI+Rh4eDSImOTV1aXLKNjo6Kh3tJjUtXV1mzlI+PjpCAgz1GUlRZeXJvb2RZUUc/EDw5PjtaT1pT"
    "VlVQTjcfUU89VlZVV1ZYWFA2ShtSOFZYWFNcVFlTO0pMG1W0t7W6v728u8CAP0CvTpSOkZiYlpmWeVharYxTjoqTl5iVl3dc"
    "Va6DiUuOkI+WmpluWFyqjIWHUIyLlI6WbFheuI6Lf4NLkI+SmFxcW7GPkoKFiEaPi49RXFmxkImMioWBRYaUUl5dtI+Oj4+G"
    "gIVGiEJXVLaPkI6Li4aJg0tGU155cXBsYVZSSUBADUI1PVZYVVZSVVJOVDgbTTtcVFVWVVdVVE86TB1WvrW1tb69wLzDwH87"
    "rEmNjZSPm56Xl5V1WauMUIyMk5qclJWXeFmsiYRIiJGPlJqdl29YqYyDhkuLi5yUl5hmW7OLjH99SImLjZOZXlmvmIyMgYdJ"
    "ipGKmlxdso2MiYiLgUqLiZJPWLiOjJiMiImFQ4iNSV2xjJGMj4mNhYJEkEVes5GTjYqNkIaDg0NBVXtwc2lhV1NHRD8+Czc7"
    "VFVSVFJXWVFSUDkZWL29u76/v7y+wr/EgLROkYyWkpicnZuam3ivi0uMk42VmZiWm5p5rpCETZGNj5WdlpueabOJiIdLiYaW"
    "kJaWlmWxiomGhkuBjZKSmJlctJWNi4eETI2OkZqXW7mSi4yJhYRKho6Xkku2lZORj4eHg0mKj5NQs42QjY+LioSEToySR7eT"
    "kZCQkIuIiYBFlkO1kpCYkIqPjoiKi0ZBenNxaGRbUk5FRT5CEWOGfW9oZF9aVFhQU0uAK3tqZlpcWUxTTktLengqamhoXmVe"
    "X19lXGxjZiloZV5kY19nYVxhZGNeLGZgZWFbXGVmX1djYFwwYWBeX15kYVpVWVhfUzBcX1poX2ZXUV5bWV1ZLV9gX2FeU05Z"
    "WlZUVlkwXGBhYFFRWGBaX1dTWyZaYVxSTVdcWltdXFZaLl5eUEpZW15cW1RaYVc0YkpJV1dcXVtdW1VZXi3L5LKztbG1qa2s"
    "sbax1H+ooKiprq+pqKqvqKueMoGHhIaKiIuJjYSmoH4uhIaMhYiLiJGKqp+CfC+Be4KJiImKjaueh4J5LYF9gIeDiIelooB8"
    "fHUyfYGDhIeJrKWHgX1+dCyBg4OIh6WpgoR+f3p1MnuGg4WmoIF/gIB7fHQshYCGqqaGhISAf3t7eS+DhqqjgoOEgIGBfHx+"
    "LoqjoYSDgoWDf4GAgYQwcoqKhXpzcmxocWtyboRXf21hXVhWU09ITkZ7eyBiWltTTVBHTUlCdWNhIGFcYF5ZWFpdVnhdWVwk"
    "ZFtbWldZW1ltUFJYVyNXV1xdV1haaVhNWVpUKFZZWVtcV2tMS1lZVlQtXFVXWFlqTUpXV1hVVC1aXVxfZ0pIWVhXVFpSLVNa"
    "XWhLRlVXWVlVVlYnWltoRUJaW1RdWldWUilYY0FAVVVaWlBXVldWKHiekIp/enBwcXBxcnOVX5KAXlhXVE5QSlFJhpJPdHFl"
    "Z2hkZmRpZIF4ch5cW0xPSk5HSD5yXWVbI1ZaXlxZXlpZb1djU1MoXFpWWltaWWVTYFJVVClYWlxcVl9tT2ZMVFZUKFpaW11e"
    "aVFeRldWUVQpVVtfXGRJYEVaVVtWWS1WWF1tTVxLXFlRWFVUKV1aa0phQlVYWFdbWVorWmlCYUVaW1dZWVZZViN2pJCXiXNt"
    "bG1nbmtpmVeeoX9UTlNMTEZNRo2WS4d2ZGBkXmJiXFuOlYJFbmNiYl5mX2VdgXluaRZRSEtJS0hER3BXXFpQI1JXVVNYV1hs"
    "UVxcSU0jVlNZW1RYZklhW0hMUSNQVlxVWWhHXl5FVFNWIlJbVlBqRl1YRE1SUVUmVFtZaERaYUFTUFZMUilWWmU/W2FGU1ZX"
    "U1RSJFhhQ1lbPVNRUlRXV1QkfK+bmJmKZWdpa2dwbaVWoqerflBLSUxGQkOQn0uHjnRbXFxdW15dj5aAS41uWF1fXl9eXJSc"
    "in9HYFtZV15aXGCBe3VoWxVES0JGREJCak1eV1FCHk1RUlNSVWNJXVpXRUofUlNUWFJlRl1bVz9LSCBXVVFTakZdVVdEUE9R"
    "IE5YUmhFXFpaQFBMU08jVVlnQVZcXUZOUk5UTyFbX0VXVV1AT1VTVE1PI3WqmpWbn4llZm1nZGejUaeosa+ASUtFR0FDkKFQ"
    "io6Sc15XXFpfVoyfiEOIjnBZXVpfVlqQoIaDSIVnXFpZW1xZlaaIiIBIWlNZWV1ZVoF6cmRiVxNCRT85PDtjRlZTVk5BHk5R"
    "Vk9UYkJWVFdWPUwfTFJRUWBCWlNVU0NISh9SS05iQVRYWFs6SkxNHFVRYERUU1VTPlJRTUseU1pCVFRYWjdOT1FOUhx4sp2c"
    "pqafhmdkaWFjplCpq6y0toBIQkJAQZSlUY6UkJF4X19hW1WWoYxOjZGOaFxhWlpdl6eEhU6KjGZWZFlfXZukj4OCR4taWFpc"
    "XliTrImFhn9FUFNWXVxZgHhxaGFTTxNEQDk8OGVAVVZQVlU9IExNVlFhQlVVWVxWO00eS1NOZ0NZVlJWWztKSSJSUWFBUVpZ"
    "U1k3TlBQJVhhOFZSVFlWPVBQT00eerSbn6ClnqOHZGZoYrNWrLGztrS3gEVGPj6TplCSlI+Zm3ZdYVxak6WHTY6QjphyXVhc"
    "XJinjo1LjI+UY15fXFqcsIiFhkyKk11ZX1lbmrGJhoZ9SIhTVV5bXpqrkY+JhYJLSVZWX1iAdnJnY1dJQhI7Pz07YUFbVlVT"
    "UFA5HktPSGQ+W1tWW1RSOEUcUVBhP1lWV1hbVT1MTCBXWjpYWVhXWVg6R0pRH3i9mJydoJ6ioIVpaGSsV7Cvs7O6vbp/QkI+"
    "kqhTjZeTmJiVeV5bWpKqg02Ok42Yl3VhXFqbqIiGTY2Tk5VrX1tlmaiKh4dRhoqUXWBbW5yykIuDhEmJkVJaYF+ZsZCTh4iE"
    "SItMVlhcnLaPko6KgoJJQ1NYWnt6c2djVExMRRA+PDlcPlJTVlhWU1I/HVBOY0NZWF9UV1NUO0kkU2Y+W1tbWFddWTtQSyB1"
    "upqboqOap6arhmplsVW3tbm5uL25vYBBQJqlT5GRlJCYl51yWViUqI1KkpWNkZiVcVhXl6uHhkyIk4+XmmlfWJywioiFTZCR"
    "lJFdXFmUsI+Ag39JiIuOT2BcmLKQkIyEgUyOklFeWZS2j4qQh4SCSItEUVGXtJGOlI6KiYFGQVlXgnhya2BZTk5ARBA6QGU9"
    "WVNPWVlUVE83HlFdPVNLVVVVW1RRPU4gdb+enp2koaOdoaeKZLRQsa6yvb6/wb2+fz+Wq1OJlZSZmJeXl3dZlaeDTIqRkpWT"
    "lp1sVperiohLjIiQlpWTZluXq4+JgkeLjJGVmFxdmK6PhoN9R4uLkpBXWpm3kZOJgopJhYiQSliXr46Sj4WGgEaHjExXm7SO"
    "kI2Hi4OFR49AV5y1jIuOkImJh4ZHQ1R+eHRraF5QTUREOw47VjtUUlNZWF5PU1I5HX3DoqGlqaOjoqOlpoe0V7m2uby8vsHB"
    "v8CAmq1PkZqal5uYoJmbdpetikqTkpaVmpibmnOWq4qHS4uNkZGSmJVqoLGGkIBKipKUkZWQYZazkIyEikeOlJOVnFeXtZKL"
    "iIeASIuFj5JSm7WPkYuJjYdIipOPSp+4koqMi4iIgEeRl0ijs5KWkpOPhIeJS5RHm72ak42Nj46KiIlJSH96c2tkXVVNSEFA"
    "PxBgjoZtaGNcV1lXUlRQhVSEeXJvb2tsbWVpZX98K2xqWllSVlJQT0VobWYpY2VgY2NeZV9eZW9fYCxmZV5dYmVmYlVsVllf"
    "L2NfYF5gYmVWZ1lbW1cvYl9gX2FjWmVVXldXWy9gYV5hX1VjTWBYWVtfMFdfXGJTaEpdW15bWVkvYV9hUWlNV1NbYV1ZVzVg"
    "Y1JjQ15SWltWXGBZLWJEXkVUVVZWXVpbWlosfpSPgoN8f3l2fXNzdIdhhG1pYF5aWVdaVFKDfi9qZl9dVlVRWlJSgm1kLGVk"
    "YmRkZmFoYnxjYV4za2BnZGliXml4XWFjZDRgZmdjZmJkbV5XYl9gNl1iX2FmZXNZWGFgY1IwYmNmZGBxVlZfY1pfWzZkYWNl"
    "cFFWYWZjWllaMGlnaGtUU11aXl5bXlsyXWNwTlFeY19cXl5hXDZmak9GW19jXl5aWmRkMtPe5LW5sravsbGsr7TVzd+wtLSv"
    "rq+ssKyw1NB+pqqkqK6qrq+lr6qsli2DiIeHiY+NkI61sJd/MYeHhIqHhoyOqKakfoIxhoeAiouFkaajoIGAdy5/f4SEj4am"
    "q6Z7f3x+MIOBiYaIoqqliIN9fHEwfYCFiKWpooOGfX5+eTGDhYirr6GFhYd+fXp8MISLqquhg4R9foiEfYcriqmuoYGMgoSB"
    "gYCAhC18n56KeXRxem1zcXNzlX6di3h4dXFtcm52bpOVWX9fXFhWVk9QT0qHhHkjW1hUUVlNTUtJenVYViZhX15gXmBdX3hx"
    "WU5aKV9XX11dZ2Fsb1FSXVUqW1pdXV5hbm1WS1xUVzBYWWFhYGpsUE9YWl5WK1peXFpsaVBMV1tYV1UtY19fbWtRTV1fWFtY"
    "Wi9fY29qSU1YW2BeWVlbLVxpZkVFW2BfX1xdXl0rfZyll4x8b29scXVzbJd4pY6JcXFra2huamWVmVWgf1dXVExQUFJMkIyY"
    "TnBqX2NgX2FjZYKFeGYdU1VPTkpKSktyclRhTSBXWFtbYWBWcG1TXExVIl5bXFhcYG1sTWBKU1MnV1pcWVZqZklkSVZTVCxc"
    "WVtYaGtLX0ZWVVRPJ15dW2psRV5HWFFWVFMrW1lrbUpeR1pdVVpXVCpaZ2tHXUNXW1xZVlpaKXedr52fjnZucnBsbHKXe6Sa"
    "m4ttb3Bsa2tlpaBbo6iAUlRSR0VFRpSNmUmKbmRhXF9fXGCVkZuKTmdbV15lXltigIV4a2EbUEVKS0dMQWhzSldbSCBVVlla"
    "WVxuaElcV0JOIlpRWFBZaGhKW2JIT04mWFdVWWdnR1hdRlZSUiVbW1trZERfWUFQVlBQKldUZGRGWlpDWVJQV1UqWWlkR1Fb"
    "O1VTUlJTUyp6qq+cnqSJb2dmaGVqoXmsmJ+kjG5mZ29maKaiV6eorYBSS0lGRkWYj5tNj5JsXV9fWF1cmpChiEqIY1pWYl5b"
    "WZiUpoaBTFlYV11eXWOCg3loYFUWSURIP0A8amNJVFhWRCFOUVNUUV5oQVlYWEJOJFRPUlRlY0RbWl4+UEgnU1dVZmJFW1tZ"
    "PlBNUCRYVWpoRlhaXj1RVVdUI1dhYEJVWl06U09RVlEjeqixnJ2goYpoaGdjZpp1spebo6GHZGdnZ2StqVGpq6utf0FCRkM6"
    "kpGhSo2MjXJaV1xjWpyRoohNjY5kW1xdX16WmqSFgkuKXVZgXFxbkZqthouAS1FWUlVcX3+De2xiVVMUQEI7PUFkXEBWWFdS"
    "Px1NTlJRYl89VFRUTz5HH1NOVGRgRlJXVVE5TkkdVU9gYEBUWlZaO0lJUSJPYmY/VFdbVj1OTFBMH3ykr52gnKGhjWhqa2eh"
    "d6+boaOooIlqaGhnqapVqbOttL6AQkRCQZqMqU+TkI+XcF5YWleckqKLS46PjGVhXVpcoZSph4NKjYpaV1lfX5ebqZSJhkuI"
    "VlxdY1qfmqyPjISBSExYVF9mg4N7aWFXSkcSPj9AOmRfQFlZVlRQQCNOVFFmYT9ZU1pTUz1EIFJTZF8+YF1aXFQ6SVEhTV9e"
    "P1hWWFZYOE9UVh98prifpaCio6GKaGppoHS4mZ2io6CihmJoX62uUbCvuLa9vX8/RD6ak6VTkJiUlJZvWlxYlZargU6Qi5KV"
    "bVxdYpKVro6HTY6Kj1xfYF6YlquLiIhIi4tVWllbkp+ujYyGgEaKTVRYYpWcrpKQh4WCSEZaXFaBg3hqZllPR0IQPT9BZmNC"
    "VldaU1NTPR1OU2JeQVlXV1dYVTdSIFVkY0BWVFNVV1I9SFAffaa6oqShoqGkpIhoZKB2spudpKWenqGNaGavpVCvr7q5ubvA"
    "gEJAkpGpTI2VlJOUlXNXW5iUqIZPiY6Klp1lWl2Wl66JjUiPiJCRY19blpuwjYmDS4aKj1ZbXJuZs4aIhoFPio5TXFeXmrSJ"
    "iY6HgkaORlJYmZeykouPh4OARklWWYGAfGxmVFFKO0IPQDxdZD1SWVtZU1NVOx5QYWU4WFlUWVVTTjZOHnOmvaGioqOipqOj"
    "h2WacraWo6GgpKOkpohksK1asK26uby9u71/PJaWpFOLjJiTmJ2YcFmWkqiEUYqSkJWgnmxcoZiviYBIkY+TmJJcXpudrYeO"
    "h0mHkJCVWFedmq+Mi4OESI6RjEpZn5izjYuNhIFJipBHVJqZs4ySh4iOgkaPR1icmbKPkI2OhYCKQ0JdgYF3bF9XV05FQ0EO"
    "PltfOVNUWFZbV1NVOR14scWdpKiipqmmqqaGo3u9m6SiqaqlpaemibqtULWzubrFvsG/w4CYl6tLkZaTkpucm59woZWsjE6O"
    "kJWWlZibbZ6Zs46HS4+JkJqamWWcmq2Ri4pMiI6Tl5NZnZu1ioqEh0uMkZWUU5ues46LjYyDTYuNk0ScnrOSkY6IhYVJjo1F"
    "mZu1i5SVj4WFh0yXRp2iuZWVlI2Tho+OSUJ/fHlpZFpXUkpLRUAWYp6ZhWhlWl1cUVFTUZNZin5xcHNpbG1ramiXfVV4b2tn"
    "bWVlbWlnf3h1KWVfXVhWT1RORmNuZ18qYF9iYGFhYWFcaGZdXTBkXmBfZ15fW25mVlpYL2VgYV9nYVdgaVRbW1YwXmZjYmJV"
    "ZGZOW1pXWi5fYWBjTmViTl1cWFdeL2JpZFNmZE1bWlhXV1k0ZmhNZGBIW1xhWVpaWDFiS2FgSV1bX1xcW1xgLoSikI18f31+"
    "enp8dm+cX5yHamlgXlpVV1hSkpJTe3NycG5zbG5paIeBdy1mYl9YWVRSVEx+ZmljLmZgYmVoZWVmdWJpWmAxYGNkYGVjZXdf"
    "bFpdWjhfZWNnZmR0WGdaW15dOV9iaGtocVZoVFtbXVo3ZV5gZHNXbE9fY19gXDZjZ2RzVmZTZWFoWllfNGhsdFNnTmBdY2Fh"
    "XGI4ZWlMZUtfX2FjXmFiXjGMo6eRh4R9fHt9dnt7mYGejX1/d3N4fHJ8dZmbaYZnZmReVlpWW1SKiIAuYWFaXFlYV1RTgHpi"
    "YzFlYWRpaGluZ3h2YmFhNWlmaGtsaW54dF1bW2M5Y2doZm1pcHNaWl5iXDJfaGpkY25yV1hlYl5aNWlmZ2lxd1dUX2BjXWM3"
    "aGlocXBXWGJkYmBYXjhraHNwWlNjY11lYV5hN2dxbVRIYF9eYF9gY2I30+Li5Li0uLGstbS3stbR3+G6tLyxsrK1s7XW09Lc"
    "sbaytbCss6y01tLRgZ+op66orq6usK2nqp8yg4uGiI+Mk42tqqabgy2Fi4OIkYmMq6mtoIJ7LYWEhoeLi6+oqJ+Dg303fn+D"
    "jI2spqWkhIJ9eTKCgIqKp6urpI6BgYN3L4aHj6ikqaWDiIl9e382iI2nq6uoiIeEgoGDfjiJr6eno4qGhIODhX+EMYCkoaWW"
    "fHhzb3Vxd26Xe56jkXJ3cnFxbXVsnJp8pI91cHJsb3J0bpqZnmCAWVRPUFFMUkyJjoN6IVdNT01NT01QeHFuU1MmW19aXF1f"
    "X3BqblFOWSlcW2BdX2FsbWtOT1ZYLVlbYlxea3BsT01XX1M0V1tdYG9saVJNXllcUCtiX1xmbG1MSldcWVRcMF9dZWxlTk5W"
    "YFxaXVgvYWptaElPWVpeXFpdYzN8paCvopR1dnR3b25ymnmjpJyRcW5vbGpubZqbd6eVkW1zb2dqc2mgnZ5Xpn9SUVNKS0lE"
    "mZORn0toZGJjZV9nYouGindfIFBNSEdJTUlsa2pMXkgkVlZXX2JbbGtnS1xIVSVUWVhYXG1rYVBYR1BWKlZdX1dncWVMX0pX"
    "W1QvW1tcbWZsS19HWlNVVSxeW3NmbURbRVRfV1FaLWBqamRJX0VZXlpXW10rf6akr6WjlnJtbXBwcKFzn7Odp49xcXJybWmf"
    "nXiroJuTcnBra2dsoqClWKutf01OTkxHR5aXl55HjWddZVtjYWmbmJSoikxfYV5mX2Rcio6HemBdG09DUEdESGtoZkhYWEQi"
    "TlZVV1VoZmxGWltCTyhTVFtWbmpnRV5dRU1QK1VgXWZzZkhcXUZVVFEsWlZrY2ZJYF5GUlRWVShZamhhQ15hQVpWV1JbKXyp"
    "prKjppyRaXBpa2qbeqGwnaKml2dnbmpqnJt4rpyeoo1oa2xsbaeno1GwrrJ/S0dEQ0WYlo+lTo2SZmJeW2RmnZeVpINLjVpZ"
    "XV9gYZ+alaaNg0lVV1ldX2CMh4Z4YFRTFD5ESEQ+ZWVoRldXVD0iUVRTV2plYUNcWVg/SiNSVVZoZGJGWmBYQ09PJlVbZ2Jq"
    "RWJdXUNSUVElXGJfWkJXVFc7UU5RUSd0qKq4oKapppNnZWVinHemtaGgoqONaGdsZZybdqafo6Clj2lrZ2SppqZXr6yxtH9J"
    "REA7lpSQnU2TkZNnXmFgXJSVlqmDTY6OXVZcYF+YmZmqholIkVVYVVxZnJKbrYeHg0dKV1hbXYaIh3tgWU9GEUY8PzxlYl87"
    "VlRUUT0fT1JWXmNiQlxYVlU8TR1LUmNnYD5WWFVWOUlNH1VhZGBDVlhXVzlOUVAee6emvKemoqaikGZiaaB0p7GZoaWeoopq"
    "aWehmXCyoKCgqKGQamJjsKunUa61sbi2fz4/P5mRk55OkY+UlmhfYV+cmJKojEuJkJNbXF9emaCZo4aGR4+OV1VcY5ycl7CL"
    "hYhKh05bWVyampmzj46HfUpKVllXiIyKeGRYUUlEFEJBOWViYT1cUlFYTT0iT0xrZGE/Wl1ZWVM7TCFRY1tfPFVVWlZTP1RP"
    "H3erqbmnpZ+fpaSRaGSYd6W4oKCgpaeejmJkmp5ysp6gp6OnpYxnZKutqFGztLO7u8F/Qj2Rm5KfTJKQl5eaaV9hm52WpolN"
    "kJSSkltcXpuTl6iLhU+Kj5dTXVuZlZqujYqHRo+UTV9anJuYs42HgoJFiElZXp6WmLWLioyIhEtHWGKAhYh6YVtPS0JEED0/"
    "YmNfPVlaWVZWUjcgVF1dXjdaX1ZfVlFAUB94rqjApKikp6Clp5Bhnm6it5qhqaWjo6eTZaCXb7Sco6KcpaOoj2Cxq6tRrba4"
    "vL/AvYA/m5KTpU6Sk5OSm5pnWpuWlqyRSYuPjpuZXlmampiuholNjZGRlFhYmZabsIqHiEiMio9IW5uYkqyOjIiCTIqSSVOc"
    "mJa2jouJin1HkkJZnJiYtI+OjYiGgUNMW4WHiXpgVFNMQkRAEztdXFs2V1ZcVVdbWD4beq+uwKeoo6ShqKOnlqN1qcGio6Wi"
    "o6WoqYyhnXG2mp+jpainpKaPubOsT7O7uLrEwMLAgJiYk6VOjpeVkpWUlnCZnZWphE+PlpyWmptgnpqSsIqHS4yOkpagWZmd"
    "nrWLjIVLi5GXkleXoJ2xj4mKg0uHi5pJnZ2et5CNkIiCT5SRTKCanrWMjoqKholNlEWco5yzkZCVjo2Oj0xEjIiDeWhjVlBI"
    "R0tGFGCmpqWDXmBbV1BVVkyeVYeNfmtvaGdkaGhpmoNKhX1qZWNjamdpXpyBgFJ2ZmlnaWZuZGeAdnRtJVdWTU5RTUxOW2Vk"
    "Xk0rVF1aXmdfWlhpaF5RTidgW1pgYl9YY2FiTFRYKV9dXVtiTWZjYU5WVlInXV9ZYVBhYVlNWVlWUC1ZYF5QY15hS1daW1ZW"
    "KmFgT2FdX0RSXVNVW1ouX09fXWFIVVdZV1laWS9+p5qZkX13dXd1c3N2m2CiooZjX1hYV1RUVJCcT4p6bm9ubWlrbWqRmYVY"
    "cWxoaWtuZG1niYF3bidbVlJQUVBOTXNZaWJWLGBeYWBgYGBvV2djUFsuYF5mW2Rea1psZFRXVytYXmRlXW5QY11MWlJWL1Zg"
    "XmFqUmBmTl5fX0wvYGJkdFRpY1NZWF1aXTReYG9PY2RMWF1ZWlxeNGBsUGFkTVhdXF1iXmExhqSknZKAfXZ1eHp8d5x9ppqR"
    "dXl7cXd4dXWgnminh2ReXV1UV1dTmJadVXxuaHBvbG1sbIuIfnMvXl1XVlNUUVR3clxkWS1jYWRmZmhjdXBWaldZL2FoZGRn"
    "ZnZvXWVWXVk2YGRmZmBtaFVmTmFiWzZgYmRmcm9XYlRdWWFcNGZkZXJuVGNQYWBhX144Zmpza1FpUmRiYGFgWzZpbmpVaVFn"
    "W2JcW2FeNoamqaecgn+BeYB4eXihg6OkloB8enJ5eXd4n6GAqZl1d3d0fnl7c6CcnGCFYGFaYmFgWlqSkYx/LF5cW1paXlRV"
    "e3Z2W1ovaGdoanBqZnZ0clhWYC9mZGRra2lxc3ZeWFxfM11nZWhpd21qWlJfW2MzYGpma3NudVZYXmBdWzpmZml4anBWWWJq"
    "YmNlPGdoc3VsVVllYWRgZF85bHRub1VTZ2FjXWNkZTzO29rd6rO4s7Sxr7S009Db3Om4t7G0srO0tNPMztnisbWytLGwrrHV"
    "0c7N3rS4sbKxs7Gx2tjQ03+mqaiosLGxsaypqKqcMYmHh4eQkI+vrqurn4kwjYiFjY2PrqqsqJ2GfS+Ff5CNiqyrrKeggn17"
    "MIGDhIaoqq6mqIeDe3wzhoSGraqopqOCh4aBgjOLiKitqKWijYiEfoKEL5Cpp6mnpIKBjYOGhIgygaKko7acfnV0dnN0dpl+"
    "m6mun3p1c3J3c3SZlHierJh3cnFvdnVxn5mafKiXcnJsbm1tcaikoaFZf1FSUVRRT1KXkZGQeCVOTE5KSVFRdXNtbVBMJ1xW"
    "WWNgYW5waW5HS1omX1lZXl9yaGhoR0pWVypTXmBgb2tqZU1IWFRQLVxfXmxxampLR1lXW1YtYmFxbWxlSUpbWldYXC9cc21s"
    "a01JVlhXWVtbMH+lpqmzqppwdW10dHmfhKSlt6SYc3BsbHdymp94oKqknHFwdHFtb6CfnnSym5htbnBvbGipqaKjVq5/TlBN"
    "TUhKnpiXkqRJXmBjYmRhaJaUkox4WxpMSkVRSUNsbHBnR1xKIFdaWlpiamdrZ0lfSk0oVltZWWhqaGVNXEFOTy9fVmBraGpm"
    "TGFJVVNULWJbb2xpa0peRVxXW1ApYGxuZmZIYElSVVhdVy1/qKamtqilm3Jxa2Npmn2kobSmo5lrbHBvbqGYe6GwqKWbc211"
    "b2qdnZt5sJ2imWxraGxqsq2opFetsX9JS09KSaKamI6kT5NcYGFmY2WbnZqXrIlLVVlfZGBmkpGTkXdWThpIRUdAQmdoZmlH"
    "Wls/I1NSWFxqZ2ZjR1lXQUsjVFlcaGtmX0VdV0RPUChYXGxrZmpJXWBGVlVUKlloZmZhR15dQlFUV1gnfKuop72opaSbaHFr"
    "b552paO2qKWpnGpoaW6im3WfsaGppJpqaWppn5qWd7Kcmp2YaWhtbbGvqaVXrq+2f0FCR0WamJaVplGQk11aW2NemZmZnaiL"
    "TZBZWl5oZJ6enpinjIZFUlhYYGaOkZOOeldRSRc+QUNDZmNlZUFUVVY6JFJQVGdiZWY/XVhaREkiUlVnZWRkQ1pfVkJPUiFX"
    "ZmZkYkJeWldCUFhUJ3uhpKjAoaKopJVpaGmkd6imtKGmm6GUZWptnZZ4obWanaOekmJfap6Xl3CymqShoZdlZGqurqylT6uy"
    "tL5/QT09mI2WkaZMkJCYYVxiWZmYmZyrh0mJkVFWW1udmJyYrYmCRopPWVxfmZqZm6uKhoRHQ1BUWo6Qjox5WVJHQBI7QT5f"
    "W2JkQVdUUE8/HktTZGJfYT5bXVlRPFIhVGVeX147VFhXVjdTVCB3pq2nuqSipaWkk2dpo3amobelpKagoJZsZ5qdeZ+1oaGi"
    "oqOaYWeempZzsKCcpJ6glmVrsq+roU6usrC9vn9CQpqWlY6nSpGUk5deW2OTmZGUqIdMjI6SU1ldlJuYlLWKiEeNk0pdYpqa"
    "kpu0jIyIS4dGWlmUmZeVs4+IgoNFRFRYj5SQkntUT01FQxM/QGRiY149VlpWVFA5H09gYWdgPFVWWFRUPU0ieKiqq8Obpqil"
    "p6eZaZp1pKW7o6Ogo6SgmWqZoXOitaSkoKWipZNknpqRbLKYnpufnqCYabKxrqtOsLe1uMK9f0Sfl5GRp0qKjpKQnF9hk56X"
    "maSGSo+QkJdVYpuWm5KuiIZGiIeXSlmWmpuYsIiFhkyJkkpbl56XnbiQhoiHSo1FW5admpu0lY6IiIdJQ1+Lj5KOeVdTSEdB"
    "QQ89YWNfXT1WXFpUU1c/HnyoqajFpJ6koqGhpJqZcqamuJ+moqWap6SVnZZxoLSdpqGjnaKjkp6ZmHKvnZaZo6CepY+xsquq"
    "Tq21trrCvbuAmZ+XjKtOkZCVmZWXW5ubkpOmh0qSj5GYlVmbm5uTqYyJRoyKlZROmZ6anK+JiIdLh4uQTJ2TmJS4iYaIgkiS"
    "jUCbm5mYtpOQhoaDRo5FnJWcm7KOkJGKiodIRYqLjYl7XE9KSUNAPQ9cqqypqoVVUFRRR0xOoFSSkI9+amRjZmNoX6qHV4eN"
    "f2dpXm1pXmGjiodSh3RkYmtjZGRmpIyIhFNoYV1lZ2VgZn52d3BnI01LSExJREdSX11fXU0nWVpUWl5aU2FkWVtOUCRWWFde"
    "W0xfXFxZS1NTJ1VXXGBNXFtaYkJRUU4rWFtfTl9ZXWJBV1ZZUipaXE5bWlpdRFdWVFNZK2JMWlxVX0FSVVFVV1Qof6mcnKaP"
    "cXZycHF0dahhr6iohFlbT1dPVE6TolmOjXprZWtqaGdml52JVY55Z2hqZ2JpYpqmjYlWbmdlZ3JpaGCJgHprZyVTTU5MTklE"
    "a1RhYWJSK1xXX1xnXW5TZlxgUFMvWl1iW11nUF1dWlRWVCxXYl9eak1iYmBNVVtSLWBjZWlLX1tkS1JgUVgwXlxqT2VlX0tZ"
    "WVpbWi9haUtiYmhGV1dYV15YLIGpsaGolnN4eXd0c3aceK2co4p3cHd1dXB5qZ5bpquHWVtWUVFQTJmWnVmRdWtqaW1paWqb"
    "lqOJV25oZ2lpam5oiIV/cmkmWFJQTFZKSXJrVmJkVitcZWBjZ15ua1ZfXk9YMGBdXV9jbG1UYGRMVlU1X1xkYGlpU15kSldc"
    "WTJjZGBwalBlaE9XXl9aNmNebW9TY2JOXFhaW1svYnBxT15lSWJgWFlcYTCApqOwpZp8eXJ6gIB5n32nrKWXd3x6eHd2b6ac"
    "gbGelHl6eHF2dnGipZ5krIhXW1ZXWVNWoZ2bpFVvbXFqbnFuc4+UjYBqKFhaVVdcU1Z2eHNZZlQtW2Jga2Fgc3JqVWVUWTJi"
    "ZmFnZm1zcFdmUmJYMWFpZ2Nsc2xVZlVgWlsyYmBhdnFtVmhPW15fYTNoYXZvc1VoVF9fYFpbOGxua21RaE9fWV9bYmA4hrKo"
    "qLekg4F7f3yCeaOGqKyvpH99eXh6fX+gm32lsp5+fXx4cn94op+efKygdXx8c3Zue7KppqVjh1tbWVlYWFSYmJaVgS5ZW1dT"
    "XVlYeHVzcllXLmBgaWNjbHV2cHNcWlcwYmhtaWhxeHRwWFdbYjVkY2pseHFwb1hPYl5eOF9qaHVwcm5ZVWZdZV01amd3a3Jx"
    "V1VhYWNjZTpndndxdFNUXWFlYl9lNdTZ39rd7ri2tLK0t7TP0tzX3Oq3uLOusri10MvO1t/ks7S1sre3tM/OytLZ37O0srSy"
    "trDU09LQztq2sK6ztbWx3NrZ19GBo6mqsrGxta+prKmloC+OiY+MlYu3pKeppp2ILYWEh5GPr6yoo6yjf4IxhoKIiaqppayt"
    "pYWBgjGEiYuoqaypqqyFfH+AMYmKr66uqbCrjomGgn4zjq6rp6aqrYuJhIaFhC2CsKOkrLekdnd2b3Z+nn6oo627pXR1eW90"
    "dZyfeaCor6Z1cnFwbnCbn5Z6pK+gcnF2b3Rwq5+cl3axoWxvb251brKsp6emXIBNT1JOTk6cn5yZmnkmSUhPT1JLb3BxbmpM"
    "RCZZVWFhYW9vbGdsSElRKFFhYmBubWppaktLVFMrWVxda29rbmRORldWVTBZXW5ubWlnSE5ZX1lYLlxtdWtkb0tKWV5aWFk0"
    "fampqbG8qqd0bXB0cp+CqKWotKylbHVuc22gmXiop7qnonV1d3B2oZyZdKCynqVxb2twaaKhnph4s5+jbG9rcW+0sq2lpFay"
    "gEZQSkhGlqCbmJilUVVaYF9mZqOdnZuXeE8cSEZHSktpaW5pZEVWRSFQVVtcaGduaGpGYUZLJ1VZXXBpbmVqS2JDUlgpXVdt"
    "b2xraUdkSFRWUitXbWxpY2lCXEdWWlpXJ4SoqqOqwKeoo3Jtcm2hf6Opqr2mp6Jra25rn5iAoKS1qKmlcG9sb5+bl3ylt6Gm"
    "omxtcWOlnpuXeLGcn6JnbG1qt7GvqqhVsLmAQExJR6Gfm5eapkyVVF9eYmWfm5+Xl6iISVFfYGVlmpmempp6U0gZRD5GQmVm"
    "aGVoSFxURSJTV11samlqZUJYV0FPKVdTa2hoZWlGXV49UVAoVGZoZ2FmQl9cQlRQVSZ6pa2mqMOknKeoZ2xtoHiipay5pqWm"
    "om5qbqGcdaKktKKfqKNuZ2Wgn5R3o7iZoqmkbWRpoZ+ZlXi1nZ6lnmhvZrOzsqisTa2vv4BAQkeaoJuOm6hHl5RVWWBdn5ma"
    "lZypi0iTTltdW5Sgm5uatYmIR0VUWlycl5SXl3pOSkcXN0JDa2FpYGRGVFhQOh9VUGFlZmZlRltcWT5OJVVlb2BkYUNZXFY7"
    "UlUieaaqpKnCo6iio6NmZ6F8qKSnu6KjoJ+iZ2qfmXSinriho6agnG1lmJqTbqK2oKCjo6RmZZifmY9vtpuZpKOhY2q2samj"
    "ok6xtbO/gDs+mZqWl42mUIuNlVVcXJWZm5yVqIZLho9QX16ampiflLKFgUiIRVdYlJmXmp6tkIWFQkNWYZicmZyUe01IREIQ"
    "QUJmYl5jXz5VWFNVQCBWZWRgZWE3WVRVWDdKHXqpqqasx6CkoaijoWabd6elqL2moaako6NvnZ16mJ+zoqOgn6CjZqGclnag"
    "spufn6CjoWSgn5eVb66enJydpKBou7a1rKZOsbe2vcSAPJKfl5ORqEmRlJiZV1uelpqUlqyNR4+Nj0tdnJKUmJesj4VAi5FI"
    "XZyWm5mas4uHiEeRRVubl5mSnLiOiIqIRURdmZeWlJZ6UktHQz0RQWJdZGBZOFldUlZbQB12p6uqrMakp6WdpKajnnilpqe9"
    "qaekpKainpqbbp6pvpykoKGkoZqgmpFzoLajnqChoaafpZ+cmXCul5qhppyepLi7tqmnSrG5uLjBw3+XnJWPlqlLlI+XmZhU"
    "nZ2ZkpGrh1KJkpOaV52ZmZiWrYWFSIqUk0WWmpuUmq+IjIZLjY5InZeTmJuzjZCEhkyTRJ6cnpubuJKIiYyMR0iak5OYmXlT"
    "TUhEPT8SW66srbG5h1RPT05QS6ValpqTlX5sZWNrZ2mpklmTj5d9bmhnaWRjpIiHVI+TdWBnZmRlYaeQiolQimlkZmZsbGSt"
    "lI2Jh1BjaV5lZm1ogHlzcWRcIUpMTkZJQ0tjYFtbVEwmVVpXXVZRYmFfWVhLUypQWVhdR2FdZFxaR1JPK1heWkxdWmJaW0lZ"
    "VVQoWlxIXWNZY11HWlVbWCxaTFxdXlxfRVRXVlNXK32zoJ6hpIpza3BwZ2qqXaesrrKFU05NT1FMmKFckJKMfGVkaWRiZZGg"
    "i1aVlHFlZl9sZWWWqI+LUYxrYmZnZmFkoKuUh4pWYF9gX2VgY4aAdnJmXR1QUEtNS0ppUl5cXllLK1lZWF1cZk5bYl5cSlEn"
    "UlxZW2tNXWNZXkNWUylYXV5nT11hXGNGU1hWKFxfZ0teWGBZRVlWVVcmYmpKWltdX0ZUVVZVUCd+p7KZoaSPcnRubXNypn+y"
    "n6OhjXZ2b3Bwb6aoX66stYZSVlRPUlKZk6JSkZV4amZmaGdtl5ipjVSSbWVmZm5obaKeqYyMU2NkZGRpaGqMiYBtZ1sgUlVQ"
    "TVJLbm1MZFRbRyRcYV9lX2luUGdgY0lVL1tbXmBwbE9gZF9PVVItWWBhbXBSWmJjTFNYWS9fYHBqU19kYkZZX1pdLGNoaUtb"
    "YmJLWFZaXF8tgquotaivnXh1eH1zdKeDpq2jqJt6eXR/eXOknX6to6iXeWt0cnhuqaWkX66zhVlVXFdRT6GcladUknNoYmNr"
    "Zmygnp2mjVZmZ2hxaGxwjo2Sf2RhIlJPU1NTU2xqa1ZkW1EzVl9iYF5wdG1SZF5QVzBbYVljcXFtUmJfT11WM2BiZG9zclNk"
    "Y1BeWFgzYWFwamxRZmpLW1xXXDRla2pqTmFmSlxjW19eN4Sxqqm6p5x7eXh6fnigg6Wqtq6deXl8fHx7pKB/orOkn3R2d3Zx"
    "dKWipH2xoZ9yeXl0eXWur6ipYK+HU1dUV1tZop2bmaZaZWdlZHJuaZuZmJuAZChYVE5SUVB2dHJvUmJOMF5gZm1pbnFwbFJn"
    "U1MyX19iX3Nucm5SYElXWDZiZGRzbGptU2tQX1xeOGZncW94dFFoVFtfXls6ZHVva3BUaVFiXV5aXzyJsKunr8Gren58d3h7"
    "rIqrq7K9qICCe4CCdaifiKqqt6p/eXd8eHWnpZyEpreifHZ5enZ4saSmn3azpHZ0eHh5eLKtqauoX4ZaWVdZV1ajoqSem34w"
    "TlNUVVlZdW9zdG5UUSxdZGRianZvcXVvT1FdMFxhYmx5d3RucFVOYF4zZWtsdHNzbXJaUltfXThnanRycW9wVFZfYV9fOWdx"
    "dnRqa1FSZGVjYV010drW1t3h77u0t7m2s8/N19bc4ey6t7a2uLjQydHV3d/ptLS3tLaz0MfG0tbb5La3uLCytNjR0NDP2OW0"
    "sraytbXY1NTS0dDZrrK4r7a03uLf3dfPgKGjqqu2uLCwrq+rraMuhoaIjo6xr6qxqaujgS+Ji4uMsLKrq6uqoIWBL4SIj6ey"
    "s6qprqyHfXwxi4yrqbCrp6apiYSFgy6OqquopK+npoqJioSIMIaqqqu0sr6wcHZwdXKjgqmnqbK9r3d2d3RxnaKApKGqtq53"
    "dHl4d5qgnHqjqbCqbnB1cnOfn56ZcqOzqm92c3BtpqOjpJ9xtqpqaHRua7Wvra2nsV5/TUhNUUyloqOln6B6IkZDSUpOc2tp"
    "bmppTEUkWVVbXWxvb2ZnZ0tEUipbW19ta2xrb29GR1RTKVlgcmtsbmdlS0pZVFowW2hxbmlnaEpMWFpZWjKAqauqrrXBqKlx"
    "dG5xoH6mpayuuqysbnR0a6CdgKWkqbupqXR1b3Gfmph7pKm8qKpxcG5xpKGXm3eptaambnFvcKWomp2fdrelq2tya3Cyr6qw"
    "q6xcsn9DR09Gn5+eppmQrEpQYF9gZaOhpqGjn3pJG0VDQ0Nsa2xsaGdFXUMoVFheamVobmdpQmFGUSVdWG9mcGtsb0tZP01O"
    "LltnZm9tZ2NJWkVWWVgsgKqqp6y0vqWqsnB1bqV8pqOmrcCpqq1xbWyfoHuio6a3raOqcG9snpyXeZ+or6anqGhubaWZm5t6"
    "prqgpa5tb26roJ+flnCwn6CqamdosbSvrLGrVbe8gUdIQ6Kkm52alalJlE5gYWGbnaCbmpuyjElIW1teoaCgm6KgekZFGkND"
    "P2hnaWJoaERSV0MjWFVvampnZFtBWlo+TiVZaGthYWVrQ1xYQFVaKX2opaemrMKjpaKuZWWXe6SjpKzGoqGlsG9qoJ57oqel"
    "wKqipalqaKCYmXiioLiiqqqsa2mfpJuUcpyum6GprGhnpaOclJxzsKChpqpmZrmysqytqlSyuLiAP0Sdm5eUnJGmSZCbTWBh"
    "mp2YlJqap4dFj0lTXKOZnZielq6Lg0dFVlqnoZ6goKN6S0dCEj1FZWZqYWFqQVdRVzsfUmNmX2VkZT9XWlg7UCN1p6Wnp63C"
    "o6Wlo6NooHijqautw6Okn5+oY56ZcKGjpr+jnKakp2yYmZJ0oJ27oKOjoqdfnZuYlHKftp+XpKaqaqGYmJ6caq2ZnZ+jqGe2"
    "tK2srqZJrrC3wH87m5iXk5CRp0yTkJNPXpyfk5eXj6iHRImWR1mVmpmcl5uzhoZDkEFZnpqblZqZto2Kh0JGWqGioqSeoHpF"
    "Qj9BD0FjXmRdY2A4WFFaVD0gd6eqo6+sx6Wio6aipJl2qKCnqsSmoaCjpaicmnmen6PDoKWko6imnpuWdJ6kt5+mnKSnpqCh"
    "mZZwnryZm6SinaaloqGfk3S0mZqio6SrvLW0rK+mR7O5vLvEf5ycmZaVkahMkY6Xm0ucmJibmJaoiE2MkpVFnpWblpyYrI2H"
    "RYyRSpqal5ugjbeLi4VJk0OYm52YmZiyjI2Lgkc/nJ6em6GgekxIQkI8EWCxsrK2u7iGUk1OTUaoU5SSmZycf2VmZ2ZopYxZ"
    "kZKRlYBgbWRiYqiLj1CTk5RzY2NmZmanlImOUZGTbWFia2RkrJGRjIpIkFxgYGphYrSWkZOJik9aYF1iZGOAeXlxZ1tVHURN"
    "SUhIUF5cYl9aVUomU1ZeWUddYVlgXlpJTSdXXF1JYV1gYl1iRU9VKWBdSWJiYV5iYUBXVlYmV01YW2JhXFs/WFVSVih9saai"
    "p6SnjXByb3JtrlqzsLa2uYdUTk1ISpqmVJKTl5x8ZWBmZWSfp4xXkpSXeG1jamlinKWQjFWPk25hZ2RpZJ6slI2JW49iZGZm"
    "aWKcrZKVi5BPXWBbZGdjhn14cWtjVB9NS09JUGZNY19bWVtFKVdWW1lrUF5hX1tWQk4qXV9dZ05gZl9eXUNUUClcYmhLXmJh"
    "YVxDV1hWLGJlSFxdX19fQVpUUlcsfqaynqmlpJBxcXZzdKF4tJmeoqmObm9vbm2qp1mpsra2hFNRTFBKlpilV5SYmXlkaGVk"
    "YZ6ToolTlo9sYWNnZGSbmamVj1iOYmBlZGVmn6GzlI2MUVxhZGhoZoaHf3JkXF0fSUdKRkhrZ09cXVpdRidWWFdfaGpNYF9d"
    "XERRK1tYYWprS2JYYWFGVFQrW19rYktbX2FiRVVWWypaamJLXmNdV0NYWlZVLX6zpbajqq+XdnFzdnOkfqazpKWsl3Bsb2x0"
    "oZ6EtJ+jq5NwcnlzdaulpWCxtLeHUk9RT0qdm5qhV5GYbmdna21spqOgqoxWkWRoamNrbaSjm6mQi1BaWWJrbGmOjo1+aGRY"
    "JE9NTU1MbGpnT2BfYkgxXltfXGdqa05iYV9NVytaXl9panBSYmFfSlVTL15gamtnT2FgZUtaWlkyWmlua0lmXmNGWVxaXC2I"
    "q6iqwKusnXJ1dXd2poKmq7eoqZ52eHN2d6ifgKO1qKedc3N3dHWkpKF8sKOnn3h0cnV0s6upp2K4uIhYUkpRVqSfoZqjWZVo"
    "aGNqaW6koaubrZFUYGZlY29qmJSbl39iXCZTTVJOVXB1c2hSX2ZML11YYmNwa21oT2phUVUxXWJkbG9pcEpmYU5WVzBhZmtx"
    "dmxTYGNNVl1gMGRwcGxyUmNkR1haWl8tia2prbHDr6xzeHp0eqKBqamyurGsend7fXionIOrrL2pqnt5eXx7pKGdfKm3p6t4"
    "enV4c6uooqN5tKOpc3Z1d3Oxr7CrpWKyh1dWV1NUq6akpJ2rUl9vam5ubqSco5udf1otU05QUVJzcXFvbVJfTyhhZGRed3Fx"
    "cnJQXk1eMmZkZnNqb29wUmJKVFs4YmZuc21wclVhU15gWzVib3V0c3NQbE5hWl1iL4awrqe0t723e4R+fnumi6urrrW+sH17"
    "fnV/pK2BqKyxu6x+f357eKmio4KnqrusfHd4d3qnqKaggqW1sXl9d3l2r6ynpqh3u7B3dHlyeLO0uK6xrlyFU1ZZWFeqq6Kn"
    "o6WALk5TUlNOc3J5eXNuVk8uX2RjaXt1dnN0blJVWjNiZ2dzc3Z2cXJSTF5iNmllcnJ0bXFuVVJfYWI3YnN2b3N3alNMYWNf"
    "ZDnS3tva3uLg7Ly2urW10tPS19zg4ey0t7O2t9DPz8/Y3d7rt7mwt7TPxs3I0trd67i1ube01tTJzNDZ3+a6ubi5udvQz83P"
    "0tnjtre0uK3Z1NvMz9PR3bW2trOz4uDg29nS0X+irKiyta+ysayrqaqeMI6Ii5KtsLCtqa+soXwyjI6OsaqwtrCysKSDgjOQ"
    "iKuqsautq6ioi4KDL4ynpKisp66wqYWGhIgvgKqtqKm6sry2cnl0eaB+o6WvrbG7tnRxenSfnXynqKWxv7N1dXFzoaCggaar"
    "scG1eHBzdKCnn6J6oKi3rXVyd3OppZ+dnXqmt65seXB2qqajqaGiebmva29sbruytrCsrLFdf0RFUEqpqaulqKukeh9ATkdG"
    "b25sb2praEZFJVBhYG5rbG50amhIRk4qXV1pa3NybmxvQ0VWWy5gcHZxa2hraEhIWlteMISvrqevtrHBqbRrdnGffKqlqayu"
    "v6mzbXd6npx+pqWurr2nsnFubpmdl4Ckpqm7qLFrdW6ioZuYgKaluqewbHh1p6KimZd7qrmgsXBybaWmnqCfm3m8n7Fkb3Gy"
    "tLiysrGsU7t/RkZKo52gmqKdm7BNR1ZXYKeqqqWoqKJ6QxxAQURvamprZ2ZmQVpDJVhcaGZpaGtpZ0lYRFMmXWpxaWprbWZD"
    "XD9VVil6qaiqra6zwamorW1ooHyopKOrqcapqa5vcKGZdp6jp6zEq6usc2qcl5V8naeqt6eksnBoopuZmm+mpbinprVoaqid"
    "op6SeJ64n6SvcGyop6CdmZt3tqCfsmxotrC1sq2vrVe6uX9DR56am5eVlpmpTI5IW2CfnaCdoJ2bsohJS15grKmoqKqgqXpG"
    "PxhCQGRmaGhpYWE+W1lAHVpkamFpZGdnRFlYPFIkeqysp6uwscSjqKGwbZ53p6Kqp7DDoKehtW2em3mepq+rwqCno7VrnZSb"
    "c6OnqLukpqC3baSamZdyoaW/n6OitWuhpKCYlm6etZqioLRloqKan5KdcbWfnp+wZLe2ubKxrqxNr7m8gEKYnp2cmJWSqkWM"
    "mElYmJqem5iXlqyKSphEW5+gmpubnZmxiolHQVmuq6yeqKmveEJAQhI7ZGBlW2VhYkRaVlU7I3qmqaimr7LEoqaip7SheKah"
    "pq2rx6ejpqetoJ93n6mmrr6ZnaimrJ2XnHKho6rBoqOlpKidop+WdaCdvZmgnaaxpKKcmZdwnrSapKGiqKmjoKGWlXGxmp6e"
    "obS3r7ezqq2xSrW1uL1/mZyZmJaUj6hLj5SQRZiblZ2Vm5epg0aQlUWblpiWm5mUs4qKSpJEnJqcmZqXlbKLkZRGQ6OkpKGk"
    "pax5Rj9BPg9huLm2ur+7vYdMS0dJrFqVlpeanZp/Y2toZKqOXZWVl6GbfGpoYGSqjpFTlJKXmnllY2RospGSiFONlZhxZmVp"
    "ZrOYk5KOUJCWZWtlY2KumZaPkYlOjFxkZWNjr5mUk4+MjFBWXGFnZoB9d3NmYVdPHEdNS0hNYmNjXl9dV0AnXFpdTWFeX1tb"
    "YVtEVShWXlBbX2BbZGBiR09YKllKYV9gYGBcW0BUUlkmfbygnaenqaiQa3BxarFWsq64ub2/iUlJUEqcqVWTmZeXo3xjZWdh"
    "m6mNWY+UmZp3ZWRnX5mvl5JUl5iXbmVlZWGgr5KMh1OQlmZfZW1mnbGRi46QUJReYmJgZ6GymJWKjo1NVmJlYWOCgXZzamJV"
    "Ux5NSElCakhkYWFhX15KJ1phXWpNYWFfX2FcRFYnW2RlSl5dXVxbXExWSSlfZkldXV5gYF1HUllTK36su6afqKmjkHBxc2ym"
    "fbWhoaKpqo1wcHFwsqlar7a1vr+EUUtMTJmXqFqTnpOXeGZnbWKcnKqVU5eUmWxmbWRlo6Krj4tXk5FhZGdrZp6kr5KPjlWW"
    "WV9nbGejnLCYjI6GTlRfZGJmiIl+c2deV1UhR0pIS2VoRl9lXGBUTClbWl1oZ0VhXWReX0pQLF1baG5JXF1cZGBHVkwsWm5l"
    "RGFgZmFcRVRPUix8p6i2rK2pqJRwcGdupXuouaGkq6mYbXVtbp+gd7CbpKaplm12cnGxq6dbsK+5uYRMTFNOnqKZpViXmJZx"
    "ZGRnY6Oin6iPXJiWZWRgZ2egnZitk4pOkV5ka2hknaCjsJeQhlNaZWhjZ4yMjIBqZVpQH0tQTEtrZmdLX2BcX0krV1tfaGZr"
    "SF1fZFhHUSpfXGtxa0hcZGNWRVZWLmZnZmlLYGFhY0lVVlUvgq+qs72rqKmgcXBzcKmBqKi6qKivnHFvcHSnnHyntp2np55v"
    "dnR0pKSae7KnpaifcHJxcLGzsa1fuLa4hVRLT1CmpZuZp1OTm2Vla2hppqGfm62QVpVcZWVoZ6Ckop+tkoxUV11qZ2mZlZiV"
    "gWNbTyFRUE1MbmdmbExbXWJKK19cYW9xcWdOYWZfRVYsWF1xaWttRF9bYUtZVC1iaW1kbEdgYmNLWFlcMYesra2wwKyrq295"
    "d3irgKepq8Cpqah1eHp2pqWCpam3p6ioeHFycqWknX2ouKSopnF4c3appZ6gfbWgpah1c3d2tKuzrahct7qFSk1TUqejnKGY"
    "sFSWYGRlcGmlpqWgoK2RVlRiaWprnp2hmpyCW1MoTk5NU25ucGxtTF5bSS1gYGN2cXBnaU5iX0ldMGBeb3FvZ21NZ2FJYGA1"
    "Y3FsbmxtUWlnSl9bXS+FraqosrO9r7J/f3Z4qYWqrqy0wqq2fXt5cqSgg6GssL2ttXp4e3OooqGCoK+9q7B4fXd1qa2dpIKp"
    "taSueXN6d6ypqZ2kgLaprHZ6cHq0tbavrK5cs4VNWFdXqqSinZmgqVVbZGZtcKiqqKWkpIFWJ05WUlhxcW9xbXBRYFIvXGNj"
    "cHF3cm9pU2JMVC9hZ3RxcHZvZFBkSVxdNmd1a251bXFTbVVcYGQ4h6+ss7S3tcC3fHp6fKaKq6upt7PCvX19f3igpI6pq7Gx"
    "wLh9fX58paWlhqypsMK5gn19fK2ppJyEqLLAtnt3eXisq6qnnX2uurd3fnp6rK6qqKyifrq2c3h4d7W6ubezsLBhhU9WVVew"
    "rKqvsKypfy1KUlFReXRxeXBzdkhRLGBlaXp3e3R1d2pQTV8zZWlydnxxdG51UVNeXTRpbHR2b3pzb1xPXmNjOdDa2dvc5ODj"
    "78K5vLbPzdLW3d/g3+22t7m3z8nP1NPZ2+Ltt7m2stHIys3L1dfd7rW6s7TY0MnMz9XX3Oi4tLO02NPKzsrO197muLe/t9XY"
    "0M/Nz9Db5La6u7LZ1tjO0NfRz+Cys7q04+He4N7X2NJ/pqusr6utsaitrrKtpS+Tk5K2r6yrrbOxraOMLI6Ur62usKyvr7Kl"
    "ko4xjqmsrKyvrq+vooqGjDKCqKWrra+vtcG5d3d1o4Slqq2os7PEvHR4daibgqWjp6uywblxdXSgmpZ9qKmsrrm1d3V4oqmf"
    "n36sqazBvHh2eKqooJ6bea6vu7p3dHWvraSkoKN2prq3cHZzrKipoaKeoHG/uHFzcLiyuLSusbG1WYBFRUytrquvrLCtqXcf"
    "QkRIcWtwbm9vamhEQiJXWnRvamtscGhrREFULGFvbW1wam1vcUNMWlQugq+ora+xsrDIrb1ycJ95oqSkqq2ywKy7c2ygnoCh"
    "pqiwscCluW9ynqGZf6Siq6vDqbZtdKCfnZV8oaStvq+5bXSonaOWnH2eqsGrum5rpqOknqCedKq8pLZpbampp6Snm5t3sam3"
    "Z2uyt7Wvr7GprVS6f0FCoaehpKGhnJ2tTEdgYq+vrLOrr62peUIdREBrZ2lta29takBXPyFbbmtqamhqZmtBXEJcKXylqa2v"
    "samwxKuotmyefKOgqa6uqcKnrrNwo5x6o6Sqra2/o624bJ+fmHWioKSswKamtmWmoZuZe5+mp7yrpbVvo6CbmJV3naS5pai3"
    "bKemoaadnXSkvKSsuGqhpKignZucdLiopLZvtLa3s7Kyra5Tur6AQZ6eoaCin5uWskucRF6in5+cmqGfmrWSR0VksrKtramu"
    "q694QDwVQWVmY2NnbmhgPVlZPSN/pKerrKuvscOmq6Kvn3qgo6+srq7Epa6otZ2ad6Wnpquuxamnq7ucm5Z1n6ipqMOooay2"
    "np6ZlHmfpqO8paaks5+hn5yTdp+jvaOnorqipJ+coJNzoryho6a6pqago5yhlm25n5+nure9tLSzrKeuULK9voCen5qdm5iZ"
    "l6hMkJdEoZ2doJucnZWrkUieR5ugmp2WmKKbt4+MSkSuqquoq6atrnhBQUEZYLu6uLS8uMDChklOTK5ZmJuVlZ+enoRoZGCs"
    "j1qTl5ianZt+ZmVjsYyOWJCYkZWad2FjYq+VjYxXkJeVmXFraGKylZaTh1WRl5pja2NpuJSPjoyGT5OTXlxqYbiUl5iPiIRS"
    "kFhgZ2eylZqUkZGOhlRSXmFhf3t+dHBhWlFHHUlMRkpZYFpgXmJXVkUmVlhFYF1fYWJgXFtDVCZaRmJhW2BgW11aSVJVK323"
    "pqKgp6Skqo1wc3KuX7W2ubm9vb6FS0tHl65WlpSYnKCgfGhmYZqoiFSTjpWanXNpZ2KerZCRVZSVmJxvZmFso7KWjI5WkpiZ"
    "aGZpZZ6yk46RiE2QlF9mZWqir5WVlI6KT5FVYmVknbeXmZiRjotSUVhhYISAdnNsYFlUSR1LQUxmRl5eYmFbVlpJJ1tXakNf"
    "YmReYl1WSVEqWWVHXFtdZF9eYENVUyeCrL6jp6qqp6qQb25vp363n6KipaqkjG5xbbWpXa+0uLvCv4dNTEydk6hUlpqYnqB1"
    "Z2lhnp+oilGVl5macWhoZ6SdrJOPWpWRl2toZGSiorCSjYtUkJNfYmZknqGylJKOiU+TVV9hapybuZiZj5COTlReXmWBiYBx"
    "amVbT0wfTElEZ2ZIXGJbVldYSChbWmVtSmFjXWFZXkpKKl5taEleYGFhZGBEU14ogK6svquopaqpkHFzcp+AprqnqqyqqZhx"
    "b3WinnyzoKekq6aVbXNtsbCrW62zurzEh0pJSKaZnalZmpqcmnNqYmulnaGqkFOWl5poZWZrm5yfrZGRVJmTZGdjaaaen7GX"
    "jYxSkFpiZGKcnqC0k5OOhldQW19ii4yOgGteW1RPIktLR2plaExmXVpbWEssXl5saG5HYV9fYFtGWilia2VoRV5iX2BeRldQ"
    "L3yxp66+qqqqoZt0cHClf6elu6iqpqqca3JzpJl5qLmipaummXRtbqKgoHGyoKGjqZt0cW+ysaunV7KyuL6GTEdHnZ+bmadS"
    "lZWXaGFlZaOmm52tj1SYl11haGOfoKCdsI2LVpVXX2dqoZ6aoLOSko9SU15dZI+TlZR/XldRTiJLS0xocWpvU2FcYFNKKF5l"
    "ZWdpYkJkYFxcRlMsXm1oaWpKXmJgYUlSXSmEqq6tscqsrKimdHZ0oH+oqrK7rKOsq3F4dKGcgqSpuaGrqaZweHGjnJ9+obWi"
    "pqundXRypqGioXi3o6arpnBvdr2ytaqwWrS5t4VSTFCloaCgn6pVmJhfaWRnoaSinpWvkVCUV2JoZKCeo5+ks4+MUU9eYGee"
    "n5qhoYBcUkwiRUpKa25scWVMYF1XSCxbXXFncWpqSmRfXkpYL2FtbWdsaklgYl9HWlkxg62vq7Gwwa6xrnlydaiEq6Str7yp"
    "r7N1dHekpYGnqqnBsKuweHd3p6CcfqaouqerrnN2b6agpp98p76oqq13eXmuqqifnXq0nqOxb3R3uLywsLaxX7S6hVFMU6Wp"
    "o6Ceoa1Tl11kaWiioJ+joqGuiU1SY2RmpaakpKijflRNIktLUG9ybGpwaE9gYEotX19wcG1ycXBOY2FHWzBhbHVpaG5pTm5o"
    "TVtcNISvrKuxs6/Cr7h2enusg6WprrC3xK+zdnx3pqaBqKutr8GvuHxxeqifonyjpLLArrZ3dXepoJ6ihKuxvqm4fXd3rqSj"
    "paF+q7mrtXp4c62pqqKon3q7orl0eXK2vbuyrrKqXrmFTVNWqKGroJ2kn7dSVmJpaK6rsKuurat/UCpNTFF0dW90cnFrS19K"
    "MWNldnNvbG9ubFFhT1wxaHF2cHF5cG1PZE9cXzSFsLCss7WztsLAfH17pIutpqqutbLGun56f6alhqqwrbe4v71/fXqho5yI"
    "r6uvtcK7e4J9r7KjpIOvsLTFv3x4fbGtpqShfay0urh6d3mwrK2pp6F+rby6fHl4srGuqKqhpYO6vHd1fL+1s7a1tq2uWohS"
    "TVe4trOwsbOyr3wrTFBTc3ZzdXZ2b25KSTJfZnJ7dXh3c29zTlJaNWtuc3R2dHVxdFFUX2U10Nzc3N7e4t/k77S7sdnT0tLZ"
    "3+Dh4e+5uLjQz87S2NrY4Nzvubm20MnI0NTQ1Nzg67S4sNLQy8XM0tDc2+26tbfU0s3Nx87U2N3ovbi01NbSzMnM0NXX5bi8"
    "utjV1NTOzczN2uO2tbnY2NbU1NLQ09Dgs7Sz4uLg3d3d3dXUf62vr6ysrq2ws7GprJ8zlJCtrLWusq2rrammgTSTra2rpayx"
    "sqyso4qMMIGrqKWtrK2ts8O5b3Oleqypq7GttLTBvnBunpZ8nKGkrKyxwrZwcZ2cl3mdpKqtsL24bWumn5mZeaOgq63Eu3Jt"
    "p5+cnaB7pqqsyLxucqenpp+dmnukq7y6b3OooqSlopmdc6+/tGdvo6WkqKCfo59svbhjb7a0s7S0urSys1KAQEaus6qosLCw"
    "tbB5Gj5DZW5ybGluaGFjQ0EkWGdrZ2RrbGltYkRDUSR8rKaksKaxsrfGrLptnn+lp6SntKyww6a/aKCYeqCipKixq8CpuHKW"
    "mJZ4oKSfqq2+p71un52bmXugqaavvqu6cqScm5+VdqOmqL2punGhop+dm5R3pKe8qb5uo6CnoZ2bmHGevqG7aqWepaSjn5ya"
    "bLufu2izvra0tLW0s69Qv4BAoZ2dn6CdnpuTs0s/Wq6xtayxr7SusHg+GzxpaWhmampnZV9CXj4jd6muq6SnrKirwaGhuKN5"
    "oqKmrbGxt8aoqLeel3egpKSqq66+pqe6m5uXcKOjoqmpxp2ms6GbmpZ5oZ+jq8GnpL+gmp+el3SioqK8nqS3paGem5uTcKCh"
    "wKWmtaKinqCbmZhxn7ufpLqioqKgnpyclm23naG7ubO7uLO1r66sULm/f56foJmdnZ2blbRFmEWbm5+UnJyblY+yjUlFr6+s"
    "qrGrsa2teTw+Fl7Aubi8v8LBwMSGTEitVZeSl5edmJujfWNcrpRUkpWUmZuZmX5jZqyMjleZkpmXoZp/Y1+vi42HUpOUl5ig"
    "cGlksZaPiYpXlI+TlGdkYrOYkpCMi1iSlZdYYWW2mJWWk4yMTpGQU2BkspWXl5CJj4VJjlBdXrWZmJWXlJCLjFNRXmF+enVx"
    "a19cUk5JH0dJR1pfY1hfYF1bVkQlXERgW15fW2JjXVxAUih7vqOjqainqKuljm5sslm0sru6vrzBwYdKTJarUJSTm52fnpx/"
    "ZmSZqY9bk5mMm5ydemdlnKuRlVWOl5SdpGtiZKC0lY6PVpCWlZ5jaGiisI+Mk4xNlJqYXmVlnrGUlZCVjFWUlVZfaZ6ymJmO"
    "jo6IUJRQYGKmuZmajpGNiolTTGJghYF8eXFmWVNMTiBKR2ZJXVxiYV9cVlhHJltpRGBdWWRjX1taRVopeLC7pamqr6apsI9s"
    "bqh5uaOlo6umpK2Nc22yrF6uuru6ucC9g01Km5moVpKTmZ2dnndnYaGWq49XlZWZmp1vZWamoK+SjVOUkZaWZmZspaKtjZWM"
    "TJOXlmFkaKKftI+WkIlPk5VXZWehnrqUjo+IhFOPU2Bin6G3l5WTk5CMUVViX4qDfnVoZlVRUEwcSUZlaEdcX2JeW1dYRiph"
    "aWdFV2FeXWZcXkRTKH2nqr2orqmnrKWTcm+je6q0nqWnqaSslHRpqKJ6sqGgpK2mqZNwdLKsp1qytLe5vcKFS0qenJypWZWZ"
    "oJmbbWRnoqSaqZFWkZqVn2NtZ52epaySklWUkZ1famSfmZ2tj5CJSZGUV2RpoJ6et5iYjYtUkUxjX6Who7OQjpWLilJXYGaO"
    "hop/bGZbVEpOIUhMZmZpSGFgY2NZYkYmYWhnYEhdX2NeW11DWip/p62qvqmnrKqsnnVvpXuoo76lp62pqZ9xbayleqK4pqSo"
    "rKiZb2ukmp18taCjpaOjnnBztKyvply0s7rAvoRLSZ2bl5emVZuVmptrY2Slo52brI1WkJiXX2VfnaCnnbWPjk+LmFVkZKSg"
    "oqKxlpCKUpBUZWSfnZ2ZrJqPjYlPT19ilI6Xk4FhWlFQTB9LSmVsaGlHXGNdXFtKKGBqZWViTFxkYWJcSVQtg66nrKvGpqqk"
    "qalyb6R/pqasv6SppKemb2ykoXigp76mqqWlq3JqpZ6bd6i4op+nraRxcaimnp19uJ6ioqiramy+tLCwqlOxtL25hEdMpJyc"
    "nJSlUZCWl1xmcqKhnp6ZrY1NlZlfYmakoJugnrGWiEyQUF5joZ6kop6zl46JTE9iYqCZmZmegFxUUEwbS0hqbGliZU9kYVdZ"
    "RSxgamZpZmlJX19ZW0dTLIepq6evtsSoqaqtb3SigKaur6/FpKupsXZwnqGBp66vwa6srK5xcKeXnXajpbmnqa6wcnWlp5+V"
    "eKa2qKersHFvqK2opJl6uZ2nq7Jxcra5s6+vrVO5vbuFSUidop6gnp2tT5eZVmZrnp6hm5mdrJVOlVJgYp2kqaWjn7CUkE5P"
    "YWKjpqqkpaOBV0tNIklLaWpoZ2hoTFtWX0cuYW1laWtqZ0RgWVxEWy2Gr6+tq7Svv6uvtnl3o4Sqp6mztcStrLF2e6KkgqSp"
    "qa/GrKy1enqopZ+CpqyqvKqntHd1pKKenXmoqrulr7J3eamfoaGig6i8qKe3d2+mrKyhoKR4uJ6ttHJ0ury5tbG1s1u3voVO"
    "TKSjoKegoJ2vUpdWZWqoqaikn6KftJFWSmRkrayuq66rqH5PSyZLT3FwbW5xcmpQYWFHK2Bsamxrc2xoUGBeSFgwibCorq+x"
    "t7fFsb98dqmEqaqzrLK1x62/eHimoYWnq6+yscKsxH96qKanhKuqq7DDsr15eamloJx+pKywu7C6d3mmrqCgmoCprb6vu3V7"
    "qqenp6Oggqu5qLh1dLCrq6qpq6F8uaW5dXW7u7W4urazsly7hkpUqaWnp6yon6C1U09sarGzr7Wvr7SwfVEnS1B4c3RwdW5y"
    "bUpkTS1dbG9wc3JsbHFKZlNaMIOur6qrs7e4usi/fH+lhqmrrbCytrrAu3l2qKSDpayvr7a7wr11eKagoYCjqq6wssK7fnap"
    "oqGafamrr7bAvHh8raelnqJ/qqewxb13eauppqehooOsrry9eHqqr6usqKSdfbG8wHZ1qqmvrqmiq6Bzvb1tbrq2t7S1t7W1"
    "tmCGTEu2sbOxs7OytK5/JktRc3RvcmxzcGpmTEwuY2p0cXFtdHNpbVFFYy/O29nY2eDh4uLg8ry60dDY1tbc493j4u+4tMrN"
    "z9DU1dvi3+LwvLPLy8fJz9PT2eLd77yy1cvHw8zS0tfd4ey2udXPyczKzs/W1uDvurPX19DMx8fO1trc7b221tbU0M/HyczV"
    "2ue4tdfY09XTz9DM093iuLfZ2NfT19PSzs3M5bS64N/j3uDk3dnY2YCxsLKwrq2tr6+yrK6mNJKtpKeqrbGtsaerq4oyeaSq"
    "nqSuq7K2rr2+aaF8paKpqqqtrq/FvGufonugpKinqq2xv71omZeUd6Chpaq0sMKza56hmZh0nZ2nrbTAvHGloZyXlXamoqiq"
    "vrtspaOgnpmYdKaip8K5bJ+jpKGenZZvoqe9vm2ppKKgp5+emnGou7phqaSkoaGkoJyga8HAZ7i1tre0tLa0tLROf0O1urWz"
    "sqmytK+vexY9Z2lrXmFnZWZoXjs4InynqK2sra+rrrDKqryheaSlpaaurq+xv6u4nJx0nKarqrCsrMOiuZeTl3KipKmkrbLA"
    "pLqfn5WXd56ko6qsv6C6o6Ohnph1oqisr72iu6Ogn56YlXOfp6q6pbyinaCfmZmad6Kjv6a7oZuko6KhmJZrpb+buKeopaGa"
    "oqCamW+8pbq2uLmztbe0sK+uT7x/nJaclpmWmJidlbdEQ7Swra+ttrOzsbJ5PxJcwLi+vMDEvcLCwoRKr1WXlJqYn56enJqB"
    "ZK2PVZCUm5Wfm52ifmKyi4xYmoyUmJyUnXpjsJCMjFeOkJOYm5t0Y7GVkomIUJGSlJ6ZZmG3mI+PjotUjZCQml5ntpeUlZSR"
    "jVSWl5tRY6+al5SOkIuNUIuUTWS6lZqTmo6PiY1SmlFkuJmamZqVlo6HjE1KY4F8enVmY1pUS0pDGEVHXFlcXlleYl5VXzwm"
    "e7mhoKKpqKWoqamPbbVcurXAvru+wLzCh0KcsVSVkpuXn6Chm35dm6yPVJOZnJ2Ym5x4XJ6wlIpSkpOUmp2dcGqksJCQlFGR"
    "kJeanWhjorSVlZCNVpSZlZldZJ20nZSOjI1VlJmZVGWktZGOlo6OiVKQmE1fn7ySl5iYj4yEU5FOZKW2l5mTk5WPjItPRWmD"
    "fXpsZ2JbWE1JQx5IYURaW1xeWmBaWF5HJn2su6OprK2gqamnjG+mfb2epKmrrqampotlvK5etrW5ub/BvsKIRp+YpVSakpmV"
    "n56gdmOinK6TV5OWmZugnG1jpZqsjI1RkpOXmaFpYZyhrJOHjk+Tj5WVXWKdobSYiZKLToyWl1NjoKG2lJSQj4NRlZZSZaKg"
    "tZGWjpKQikqNSmCgoriWl5aXkouQUUpjhYV/b2hhXVVHSUwcR2ZiRl1gY2RbYGNeQih7rq25o6apqKOqqpZnpHylvZ6jrKWp"
    "p6yUbKGhfLKhpaern6atk2q3saxXsbu2usHAwoVMoJuWqlqalJWbnqFxZKWanKqOVpaUmpmca2Smp6Cui5BUkZSYnltnnp2k"
    "sJOPklSNl5dhZp+io7eSmImOT5SSUmKgnZ64nZWNk4dRk1NrnKOjt5admJGPjVJMaYqTkIFrZF1XTk5IHkdlY2hHWVtcXFxc"
    "XUYof6+srMarraaqqKmeb6F7pKq5oqqmqKCwl3KtnHunuKWlpaKopqBqpJ+cd7Gkn52ppaafbruzraZdtrW2vMHChk2ioJ2X"
    "qE+YlpaaoGlknJ+bma6PWJiTm55hZqGeoJ6sjY5SkZSWV2WkoqKju5KQi1OTlFZpnpucnr2VjpCITZZOY6edoJ64mpeOipNS"
    "TWaZmJeUf2NfU1NKTB5LcG5lbUpgY2VfXGFCLICsra2wyKWmqqmtqHWjf6unrLmsrKerpqFypaCCpKW8oamlqKSoa6OinHip"
    "uqGip6Klq2+tp5uacrWhoqWkqahxu7Sxq6pUt7i5ucGFR6KmnZWXq1makKSVX2ednp6fn6qRVJOWnlZom6Ojm6Cym5FQj5BR"
    "Z52hoqCbtY+RjFKRUGOgnp2fo7CXjZGMUFZpnJ2em5yBVlROS0shSWhnamptRGFeXWJdSi2Aq6mtqqzBpqanqqxwpH6ip6mx"
    "waakqKavcKSjgZ+ipsKlo6imqHKenKJ7n6u5oqqmpqxqoqKdnnekup+goqWsb6imo6CecbGboqSqrW24urm0q6lWtLS+voVN"
    "nqOdmpyeqleQmJ5Qap+km5ykmK+KUJeSVF2fnZ6gn5uxk5BUl0tkn6ChnJybs5WNj1BNZ6WkoqKgqX1XTk1EHEpmaGhnaGRF"
    "XWBcYUAlgq+vqbOyscaop624cat+paiora3IqqyrsnGpoXehqq2uxKunrLFspp6afaOgrbyppqmzcaymn5t7paO5qaapt26p"
    "pqegnnamt6Gjp7R3paampKSgdrWmpai6c7+8urSyrK1XvLbBh02do5+pnp6brk2UlVBko6Kmn6OgnK6MUp5RaqKjpJyinqSv"
    "kpVNS2erp6qorKuofkhKTBxKbnFsZm9tbEpeXGBIKIa0qqistLWxx6+xu3elg6ikrLGuscKrq7t1o6F7pqWvqrbFqqy6eaWe"
    "nn6lqKutxqypvXKqpZ6fgaioqb2uq7h1q6Wln5x5oKvCpqy4dqqpoKOgnnumwKWuvXKoqKqlqaGgdLqnpL10uLO4urS2tqxa"
    "u7+HSKSpoaSjoZ6esVacT3Ckqaimo6ipnrWZU1BitLK4sayxsbeASEklUGtxdGt0b29xSmJkRimGsK+pq6+ys7TJq8B1noOp"
    "pqursq+zxLC7d5+egqaoqKi2tsiqvHClo6F8oq6prrbErbtxpKOfm32npKqww6++daykpKWcfaaprsGqvHOkqqWooaB6q7LB"
    "qMB0qaeppaKfnn2pu6a/brCpqammn6Ohbb6ov3C8trW5ubW4sK1ZvIdNqaennaSmoJ6bs1FQarW2trG1tLK1t39OIkptamtr"
    "cWtub2ZKYE0piKqlr6+3r7SytcfBdKiBraWtsLSvs7bIxHamo3ikq6qrrq6txL5xp52egaelqq6ys8i/cKWhpKB7o6+rra3G"
    "vnimpaSkmoGnra+xv8Jzp6iio6SgfKWxscS+famppKafpJ18pKy/vWuntrOpq5+ionGrwMNzq661paynpKOlfr7Bcru4ubm1"
    "uri4srNZhEi8vLO3s7S7s7axgSRMbGxsb21uamhqaElKMNXb19fb4eDe4OTk9LnL0dbU297h2t/b4fG20snU0tXV3N3e3+Hx"
    "ts7HyMfQ0tfa4N7f7LPRy8nG0NDW1d7e4PC31NDQx8XM0dTX2t/uuNPZ08vFxtHP0drg8LjZ09XNz8rI0NHZ4u251dbT0dLK"
    "ycvO097qtdnV1dbT0M/Oysvb5Lba2dXZ19PR1NLRy+m75+Hj4eHe4+Pa3duAtKqqq663rK2rq66yri1+q6elpq2trKytssi+"
    "nXWnpaekrKeorK7Et52ZdaOlpqiwsqqvwb2dmph2np+mo6quq8S7oJ+Wk2+jn6aoq7DCup2enZOYcaOoq6qpvrelnZyam5hx"
    "pKSmrb7AqJ2lpZudnXOfoqXEvKagpZmdnJiWcZ6kvrulpqGdoZ6el5Rsp8O6o6Senp+fnp+inG3CvLq3uLi0trW1r7WzS4Cz"
    "s7Gqr7StsrC0rXsSZMLBwsPEvLrAx8TEhbVcnJaeoKWepZmiqYC7lVaWmJaenaCbnqSAtJaOUJWVlZ2enKKic7CTkYtWjJOX"
    "mZqfnnWzlo+RiVGSkpmamp1ls5WXlIqOVZeYl5ycY7KalZaPkIxYj5Wbm1y1mZGYlo6Kk1aQkZpRuZqSlJKSk46RUpiWULuW"
    "lpeVlZKTk5VSmEu4npmaj5eZkZSSk1VMfnh3cmtdXldMTE1DHoLDpqWoqqSsqamjq4y2Xr69vLq9x8XBwsSFobBRmZSbn5mh"
    "nJqgg56zkliSlZegm6Sio3egr5WRWJKRmZmhnpx0pbSOlIhUipOXkJuibKO1lpWQiVSOmZSZoWGnt52Rj4qJW4mOlZ9bnraa"
    "mZKTlItTkpSZVZ24l5qXkoqJjFKUllCfu5iYmpmalZCLW5ZPo7udnJGYl46OlZNVTId/e2tzaF1WVkxKTB+BscirqauprK2n"
    "q6qOqHu/nqaoq6mnpKyrjLq5Xrq4uL3AwL/HxoafmqtYl5uepZ+goaR8op6qkFaTmZmboJigcqOdsJKOWJSWmJ+fm2yipbSV"
    "lItXkZCeoJthpKO0lJOLkFeOlp6aW6Ciu5abkZGJU5KVnFSeo7aXlpiWj4tUmJdTpJ+6n5qWlpOPjliUUqaluZealZeTi5ST"
    "VE6IhH91bmhcVlFSR08dga2txq2prKarp6qtl6h8qrqkqqutpqS0rZSrpH66oq6qq6epp6yWtrS3XLa2vL28w8jJhp6blqpY"
    "lJmenaGfonaqnaGui1mbnJ6bmp9noaSksY+VW5aSnpqiZJ2iobaNjIxTlJWWpF6fop60k5OKkFOPlZxXpKShupWTl46JWpuZ"
    "VaGiqLedmZSUjI5VoVCjpKK4kpWYmZSUkFFVjZSKf29lW1pSVFBIIn+qp67Dqqulqqypq5ujfaqlwqKnq6ekqqybqqBzpLyk"
    "paipq6arm6Kgn3WwoKGoqaqlqJe3sq6sW7K3uL3Ew8KEoJeal6xVkJaZnp6mZqOinZ6rlFCYmJqbnF6eoJyZrYyIWJeUm5pb"
    "n6Gfn7iSkoVQlZeYVJ+in6G1lZGGi1OUlU6gpp6ispaVjI2SUp5SoaOfprWSl5CLjpJIUJSMkZB+YVpVU0hLSh98rrGtrsao"
    "pqujqq2konqlpKy/paaop6qmoqmcfZ+oxKKkp6yrp6WkoKB5prqeq6eqoKmcqqeYmH22n6Ghq6qpo765trCrUrS9vbzIx4ag"
    "oJ2Zlq5Yl5yUmp9fo6CioZyvlVGUkpieWp+fmZ6fro6MUZKVkVmfm56dobaWj4pOk5VUpJuhoKO2mJOTi06YSaahnKSfu5uS"
    "kJSRU0uil5eanoBbWlFNSUMegainp7Oyxaimq6ioraR8paiusMippqiqp6qpoXugpKrFqamqpqmooJ6he6Wmvqiopamjqaii"
    "pJ5+qbaipaepo7CtqJ2gonS1o6Cmpqasurm0ta6tWbW2vMDHhaSgqJybk6xPl5mYnVOjn56enZaskFCQmZdSpKCeoJ2fsZKO"
    "TZaYTp2copyboLuXk4xSmkyhpZujnJ66k5CRlVJSoaKjpKWkfVJRTklMIIGvrKqvtazJqKaqprGigK+mraqxwqeipKGyoqF+"
    "oKOsrMKnqKqkraOcn3yhoaXEqKmgqq+mo52ccqetvaiop6W1qqifpp52prijo6uisqurp6Odm3WzpaOop7PAvry5uLGyVre8"
    "u7uGpKKjnJyYkqNQjpSfUaKhm5+fnZGwi1OSmlKcoJmhnqCfr46WTplMnZ+ko5qhorWOkJdUTaipqaWqpa2ATk1JTR2Fr62q"
    "srKzssesq666pH6opqussK/Fpquwt6WlfqOmrbCxx62sqLWjoaB8o6Wprsasqai3qKKjonyoqq69qaurtq6np6Cae6Gpvamq"
    "rbeoqqmcopp2p7qnpa63p6Wnpqeennq3o6alub+4ura0taqwXby+woeln5+hnqCXm65TnaBSoqSjpJ2mpp+1kliXTqGln6Og"
    "op+htZmVVE+zqa6trK6usYBOTUwkf7CrqK+xq7SzxLCtuqp/qamoq66vuMSurL6kpX+iqa2us7DCsay0pJ6feqWoqLGxwK6k"
    "uKadpJx5pqerr8irrLyqqKaknXmlpavEp6m7qamlpKGcdaWpv6elvaqrpaOlpZx5pcCnqcCrrauqp6CjoXWzo6a+try7uba4"
    "srCrXLu9hqOloaKjpKOhma5UoU2qp5yjo52jo521l1FLs7Otq7eysbKxf0hNJYarqqurrrK1tLXFr8GmfqimqLKxsLWvwq2/"
    "pZt/oaWsqa+rt8mquqOdnICipK2urqu/p7SloZ6be6SiqKeswqi/qKGjnaB6p6Wvrcikwqyqo6ClnnumpqrEq72tramlpaKg"
    "e6Sqw6q+raawqaakn5x5pb2mvq2qrKitpaSjoHW8ocO/uru8tri7t6y6VMSGoKGhop6inp+bn7ZNUrK1uK+0tra2srd/SyB8"
    "q6enrLOzs7Gzs8a9oXupqauwrbKutLHGwKWbe6KlrK6zqa+xxr+foZ17nKKkrq+wr8G5pp6hmnekqKerq7LAwqunnp+ae6ao"
    "qqq1v8Cor6ChoKJ3paelr8LDqaiqo6Cdm3ehqa3Ewaasraqjopucc6ujwr6qrKGvoqajoJpzrsHBraWspauspKelnHXHwMO4"
    "vbm9tb+3ubK1UYS8s7C3tbyysrOytIAh0N3d3d7e4eHe5OLm7tLP19zb3OPh4N/f4u/TzdLU1tXc4ODg4eLp0c7IzszU1tjh"
    "4ODk69DOycPNz9LY2N/d4fDX08/HytLL2Nnd4uLt1NjSyMPKz83T1tzf7tfT0tLS0MbQz9bb3PDZ1NPQztDHxs3R1tzm1NjX"
    "0NbOy8vKz9vc6dfW19XS09LPz9DN3e3Z2dfX09La19bWz9Lt4eDi3eDh3+Lb2t/efw=="
)
_PF = {"S":[1,1.5,2,2.5,3,3.5,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,20,22,25,30],"tab":{"1_1":[1.0,[0.9888]],"1_1.5":[0.9958,[0.9888]],"1_2":[0.9292,[0.9888]],"1_2.5":[0.8581,[0.9888]],"1_3":[0.8046,[0.9302]],"1_3.5":[0.7738,[0.8374]],"1_4":[0.7474,[0.7518]],"1_5":[0.7222,[0.6181]],"1_6":[0.6842,[0.5414]],"1_7":[0.6569,[0.4862]],"1_8":[0.6353,[0.4442]],"1_9":[0.612,[0.4023]],"1_10":[0.5789,[0.3682]],"1_11":[0.5559,[0.3481]],"1_12":[0.5276,[0.3254]],"1_13":[0.4933,[0.3054]],"1_14":[0.4807,[0.2878]],"1_15":[0.4613,[0.2721]],"1_16":[0.4486,[0.2567]],"1_17":[0.4249,[0.2381]],"1_18":[0.4147,[0.2273]],"1_20":[0.3915,[0.206]],"1_22":[0.358,[0.1953]],"1_25":[0.3379,[0.1713]],"1_30":[0.2745,[0.1495]],"2_1":[0.9829,[0.9888,0.9888]],"2_1.5":[0.8973,[0.9888,0.9888]],"2_2":[0.8131,[0.9888,0.9888]],"2_2.5":[0.7082,[0.8908,0.9888]],"2_3":[0.5976,[0.7464,0.9695]],"2_3.5":[0.5137,[0.596,0.8421]],"2_4":[0.4709,[0.5063,0.7081]],"2_5":[0.4007,[0.3874,0.4991]],"2_6":[0.374,[0.3311,0.3911]],"2_7":[0.3462,[0.2975,0.3374]],"2_8":[0.3301,[0.2639,0.303]],"2_9":[0.315,[0.2407,0.272]],"2_10":[0.3011,[0.2227,0.2512]],"2_11":[0.2855,[0.2068,0.2294]],"2_12":[0.2655,[0.1924,0.2143]],"2_13":[0.2524,[0.1819,0.1966]],"2_14":[0.2395,[0.1685,0.1868]],"2_15":[0.2321,[0.1628,0.1795]],"2_16":[0.2205,[0.1569,0.1683]],"2_17":[0.2109,[0.151,0.1608]],"2_18":[0.2025,[0.1471,0.1548]],"2_20":[0.1892,[0.1395,0.1473]],"2_22":[0.1723,[0.1349,0.1405]],"2_25":[0.1604,[0.1278,0.1333]],"2_30":[0.1422,[0.1198,0.124]],"3_1":[1.0,[0.9888,0.9888,0.9888]],"3_1.5":[0.9758,[0.9695,0.9888,0.9888]],"3_2":[0.8283,[0.8216,0.9888,0.9888]],"3_2.5":[0.6754,[0.6552,0.8842,0.9888]],"3_3":[0.5355,[0.5129,0.7179,0.9626]],"3_3.5":[0.4542,[0.419,0.5661,0.8296]],"3_4":[0.4007,[0.3639,0.467,0.679]],"3_5":[0.3452,[0.3015,0.3544,0.4643]],"3_6":[0.315,[0.26,0.3036,0.364]],"3_7":[0.2876,[0.2274,0.2637,0.3105]],"3_8":[0.2608,[0.2024,0.2349,0.2688]],"3_9":[0.2432,[0.1873,0.2104,0.243]],"3_10":[0.2272,[0.1703,0.1929,0.2169]],"3_11":[0.2145,[0.1616,0.1786,0.1993]],"3_12":[0.2046,[0.1534,0.1681,0.1867]],"3_13":[0.195,[0.148,0.1596,0.1739]],"3_14":[0.1802,[0.1419,0.1524,0.1654]],"3_15":[0.1738,[0.1385,0.147,0.1583]],"3_16":[0.1673,[0.1348,0.1431,0.1528]],"3_17":[0.1612,[0.1314,0.1391,0.1486]],"3_18":[0.1535,[0.128,0.1347,0.1434]],"3_20":[0.1455,[0.1234,0.1295,0.1363]],"3_22":[0.1381,[0.1191,0.1252,0.1311]],"3_25":[0.1305,[0.114,0.1193,0.1242]],"3_30":[0.1233,[0.1098,0.1133,0.1173]],"4_1":[1.0,[0.9888,0.9888,0.9888,0.9888]],"4_1.5":[0.9807,[0.971,0.971,0.9888,0.9888]],"4_2":[0.8282,[0.8219,0.8219,0.9888,0.9888]],"4_2.5":[0.6601,[0.652,0.652,0.8859,0.9888]],"4_3":[0.5136,[0.5017,0.5017,0.7105,0.96]],"4_3.5":[0.4205,[0.4058,0.4058,0.5511,0.8212]],"4_4":[0.3735,[0.3506,0.3506,0.452,0.6681]],"4_5":[0.3144,[0.2829,0.2829,0.3426,0.4484]],"4_6":[0.2767,[0.2415,0.2415,0.2869,0.3533]],"4_7":[0.2487,[0.2106,0.2106,0.2472,0.2956]],"4_8":[0.2283,[0.1892,0.1892,0.217,0.2557]],"4_9":[0.2111,[0.1721,0.1721,0.1966,0.2251]],"4_10":[0.1934,[0.1608,0.1608,0.1795,0.2047]],"4_11":[0.1821,[0.152,0.152,0.1674,0.1864]],"4_12":[0.1738,[0.1456,0.1456,0.1594,0.1746]],"4_13":[0.1643,[0.1411,0.1411,0.1519,0.1654]],"4_14":[0.1552,[0.1351,0.1351,0.1454,0.1572]],"4_15":[0.1509,[0.1322,0.1322,0.1414,0.1521]],"4_16":[0.1453,[0.1291,0.1291,0.1373,0.1467]],"4_17":[0.1408,[0.126,0.126,0.1334,0.1416]],"4_18":[0.1378,[0.1235,0.1235,0.1307,0.1386]],"4_20":[0.1314,[0.1183,0.1183,0.1245,0.1325]],"4_22":[0.1272,[0.1153,0.1153,0.121,0.1278]],"4_25":[0.1209,[0.1112,0.1112,0.1159,0.1205]],"4_30":[0.1154,[0.1075,0.1075,0.1114,0.1155]],"5_1":[1.0,[0.9888,0.9888,0.9888,0.9888,0.9888]],"5_1.5":[0.981,[0.971,0.971,0.971,0.9888,0.9888]],"5_2":[0.8294,[0.823,0.823,0.823,0.9888,0.9888]],"5_2.5":[0.6513,[0.6467,0.6467,0.6467,0.8839,0.9888]],"5_3":[0.5028,[0.4961,0.4961,0.4961,0.7085,0.9589]],"5_3.5":[0.4072,[0.3983,0.3983,0.3983,0.5457,0.8186]],"5_4":[0.3588,[0.3456,0.3456,0.3456,0.4469,0.6638]],"5_5":[0.2958,[0.2759,0.2759,0.2759,0.3367,0.4431]],"5_6":[0.2569,[0.2341,0.2341,0.2341,0.2782,0.347]],"5_7":[0.2274,[0.2018,0.2018,0.2018,0.2374,0.2846]],"5_8":[0.2076,[0.1821,0.1821,0.1821,0.2094,0.2469]],"5_9":[0.1884,[0.1658,0.1658,0.1658,0.1883,0.2176]],"5_10":[0.1776,[0.1552,0.1552,0.1552,0.1729,0.1957]],"5_11":[0.1655,[0.1482,0.1482,0.1482,0.1631,0.181]],"5_12":[0.1571,[0.142,0.142,0.142,0.1549,0.1702]],"5_13":[0.1494,[0.1368,0.1368,0.1368,0.1477,0.1612]],"5_14":[0.144,[0.1323,0.1323,0.1323,0.1421,0.154]],"5_15":[0.1401,[0.1295,0.1295,0.1295,0.1379,0.1485]],"5_16":[0.1361,[0.1261,0.1261,0.1261,0.1338,0.1435]],"5_17":[0.1334,[0.1234,0.1234,0.1234,0.1314,0.1396]],"5_18":[0.1301,[0.1202,0.1202,0.1202,0.1277,0.1364]],"5_20":[0.1246,[0.1165,0.1165,0.1165,0.1224,0.1298]],"5_22":[0.1207,[0.1134,0.1134,0.1134,0.119,0.1251]],"5_25":[0.1159,[0.1097,0.1097,0.1097,0.1149,0.1188]],"5_30":[0.1097,[0.1059,0.1059,0.1059,0.1096,0.1134]],"6_1":[1.0,[0.9888,0.9888,0.9888,0.9888,0.9888,0.9888]],"6_1.5":[0.9812,[0.971,0.971,0.971,0.971,0.9888,0.9888]],"6_2":[0.8296,[0.8231,0.8231,0.8231,0.8231,0.9888,0.9888]],"6_2.5":[0.65,[0.6462,0.6462,0.6462,0.6462,0.8839,0.9888]],"6_3":[0.4974,[0.4947,0.4947,0.4947,0.4947,0.7077,0.9586]],"6_3.5":[0.4011,[0.3961,0.3961,0.3961,0.3961,0.5441,0.8181]],"6_4":[0.3474,[0.3403,0.3403,0.3403,0.3403,0.4423,0.6614]],"6_5":[0.2833,[0.2706,0.2706,0.2706,0.2706,0.3326,0.4398]],"6_6":[0.2425,[0.2273,0.2273,0.2273,0.2273,0.2722,0.3423]],"6_7":[0.2146,[0.1967,0.1967,0.1967,0.1967,0.2325,0.2809]],"6_8":[0.1939,[0.1769,0.1769,0.1769,0.1769,0.2054,0.2415]],"6_9":[0.1791,[0.1626,0.1626,0.1626,0.1626,0.1844,0.2141]],"6_10":[0.1648,[0.1524,0.1524,0.1524,0.1524,0.1693,0.1915]],"6_11":[0.1561,[0.1453,0.1453,0.1453,0.1453,0.1601,0.1779]],"6_12":[0.1486,[0.1392,0.1392,0.1392,0.1392,0.152,0.168]],"6_13":[0.1431,[0.1347,0.1347,0.1347,0.1347,0.1455,0.1583]],"6_14":[0.1387,[0.1308,0.1308,0.1308,0.1308,0.1402,0.1519]],"6_15":[0.1345,[0.127,0.127,0.127,0.127,0.1361,0.1463]],"6_16":[0.1312,[0.1245,0.1245,0.1245,0.1245,0.1327,0.1423]],"6_17":[0.1279,[0.1215,0.1215,0.1215,0.1215,0.1296,0.1382]],"6_18":[0.1249,[0.119,0.119,0.119,0.119,0.1259,0.1349]],"6_20":[0.1207,[0.1153,0.1153,0.1153,0.1153,0.1213,0.1282]],"6_22":[0.1172,[0.1125,0.1125,0.1125,0.1125,0.118,0.124]],"6_25":[0.1121,[0.109,0.109,0.109,0.109,0.1139,0.1183]],"6_30":[0.1072,[0.1054,0.1054,0.1054,0.1054,0.109,0.1128]],"7_1":[1.0,[0.9888,0.9888,0.9888,0.9888,0.9888,0.9888,0.9888]],"7_1.5":[0.9812,[0.971,0.971,0.971,0.971,0.971,0.9888,0.9888]],"7_2":[0.8296,[0.8231,0.8231,0.8231,0.8231,0.8231,0.9888,0.9888]],"7_2.5":[0.6491,[0.6459,0.6459,0.6459,0.6459,0.6459,0.8838,0.9888]],"7_3":[0.4959,[0.4944,0.4944,0.4944,0.4944,0.4944,0.7074,0.9584]],"7_3.5":[0.3969,[0.3946,0.3946,0.3946,0.3946,0.3946,0.5424,0.8176]],"7_4":[0.3425,[0.3384,0.3384,0.3384,0.3384,0.3384,0.4399,0.6598]],"7_5":[0.2764,[0.267,0.267,0.267,0.267,0.267,0.3302,0.4383]],"7_6":[0.2364,[0.2242,0.2242,0.2242,0.2242,0.2242,0.2696,0.3394]],"7_7":[0.2048,[0.1929,0.1929,0.1929,0.1929,0.1929,0.2284,0.2777]],"7_8":[0.1867,[0.1742,0.1742,0.1742,0.1742,0.1742,0.2018,0.2377]],"7_9":[0.17,[0.1604,0.1604,0.1604,0.1604,0.1604,0.1811,0.2105]],"7_10":[0.1586,[0.1512,0.1512,0.1512,0.1512,0.1512,0.1676,0.1896]],"7_11":[0.1503,[0.1436,0.1436,0.1436,0.1436,0.1436,0.1589,0.1762]],"7_12":[0.1448,[0.1382,0.1382,0.1382,0.1382,0.1382,0.1512,0.1667]],"7_13":[0.1394,[0.1337,0.1337,0.1337,0.1337,0.1337,0.1442,0.1571]],"7_14":[0.1347,[0.1296,0.1296,0.1296,0.1296,0.1296,0.1392,0.1504]],"7_15":[0.1303,[0.1258,0.1258,0.1258,0.1258,0.1258,0.1351,0.1453]],"7_16":[0.1273,[0.1229,0.1229,0.1229,0.1229,0.1229,0.1317,0.1412]],"7_17":[0.125,[0.1207,0.1207,0.1207,0.1207,0.1207,0.1287,0.1373]],"7_18":[0.1221,[0.1181,0.1181,0.1181,0.1181,0.1181,0.1252,0.1339]],"7_20":[0.1181,[0.1148,0.1148,0.1148,0.1148,0.1148,0.1206,0.1276]],"7_22":[0.1139,[0.1116,0.1116,0.1116,0.1116,0.1116,0.1174,0.1234]],"7_25":[0.1103,[0.1086,0.1086,0.1086,0.1086,0.1086,0.1136,0.1181]],"7_30":[0.1053,[0.1048,0.1048,0.1048,0.1048,0.1048,0.1085,0.1124]]}}

# ---------------------------------------------------------------- tables at import
_raw = base64.b64decode(_EQB64)
E = [[_raw[i * 169 + j] / 255.0 for j in range(169)] for i in range(169)]
del _raw
W = []
for _k in range(169):
    _r, _c = divmod(_k, 13)
    W.append(6.0 if _r == _c else (4.0 if _r > _c else 12.0))
VSRAND = [sum(E[h][x] * W[x] for x in range(169)) / 1326.0 for h in range(169)]
ORDER = sorted(range(169), key=lambda h: -VSRAND[h])
PW = [0.0]
for _h in ORDER:
    PW.append(PW[-1] + W[_h])
RANKF = [0.0] * 169      # fraction of combos at least as strong (midpoint)
for _i, _h in enumerate(ORDER):
    RANKF[_h] = (PW[_i] + PW[_i + 1]) * 0.5 / 1326.0
PRE = []
for _h in range(169):
    _row = E[_h]; _acc = 0.0; _p = [0.0]
    for _x in ORDER:
        _acc += W[_x] * _row[_x]; _p.append(_acc)
    PRE.append(_p)


def eq_top(h, f):
    """Equity of class h vs the top fraction f of hands (by equity vs random)."""
    if f >= 0.999:
        return VSRAND[h]
    x = f * 1326.0
    if x < 6.0:
        x = 6.0
    i = bisect_left(PW, x)
    if i < 1: i = 1
    prev = PW[i - 1]; wh = W[ORDER[i - 1]]
    num = PRE[h][i - 1] + (x - prev) / wh * wh * E[h][ORDER[i - 1]] if False else \
        PRE[h][i - 1] + (x - prev) * E[h][ORDER[i - 1]]
    return num / x


PF_S = _PF['S']; PF_T = _PF['tab']


def pf_lookup(m, s):
    """(push_frac, [call fracs]) for pusher with m players behind at s bb (interpolated)."""
    if m < 1: m = 1
    if m > 7: m = 7
    if s <= PF_S[0]: a = b = 0; t = 0.0
    elif s >= PF_S[-1]: a = b = len(PF_S) - 1; t = 0.0
    else:
        b = bisect_left(PF_S, s); a = b - 1
        t = (s - PF_S[a]) / (PF_S[b] - PF_S[a])
    pa, ca = PF_T['%d_%s' % (m, PF_S[a])]
    pb, cb = PF_T['%d_%s' % (m, PF_S[b])]
    return pa + (pb - pa) * t, [ca[k] + (cb[k] - ca[k]) * t for k in range(len(ca))]


PAY = [10, 7, 5, 4, 3, 2, 1, 0]


def icm(i, st):
    """Exact Malmuth-Harville ICM equity of seat i for payouts 10/7/5/4/3/2/1/0.
    points(place k) = (8-k) + [3,1,0..][k]; P(i ahead of j) = si/(si+sj) in Plackett-Luce."""
    si = st[i]
    n_other = 0
    T = 0.0
    for s in st:
        if s > 0: T += s
    if si <= 0:
        for j, s in enumerate(st):
            if s > 0: n_other += 1
        return PAY[n_other] if n_other < 8 else 0
    v = 7.0 + 3.0 * si / T
    for j, s in enumerate(st):
        if j != i and s > 0:
            v += -s / (si + s) + (s / T) * (si / (T - s))
    return v


# ---------------------------------------------------------------- the bot
OPEN_THR = {0: 0.0, 1: 0.48, 2: 0.36, 3: 0.26, 4: 0.20, 5: 0.16, 6: 0.13, 7: 0.11}
COMBOS = []
for _a in range(52):
    for _b in range(_a + 1, 52):
        COMBOS.append((_a, _b, cls_of(_a, _b)))
COMBOS.sort(key=lambda t: RANKF[t[2]])
COMBO_RF = [RANKF[t[2]] for t in COMBOS]


DEBUG = False


class Bot(Agent):
    MC_BUDGET = 0.00025
    PF_MAX = 16
    WILD_PFR = 0.28
    WILD_AGG = 0.5
    OPEN_SCALE = 1.6
    VTHR = 0.58
    VTHR_STICKY = 0.50
    MARGIN = 0.04
    CBET = 0.55
    CALL_SCALE = 0.8
    RAISE_EQ = 0.80
    FOLD_TAX = 1.0
    LCB = 0.0
    COND = 1
    COND_KEEP = 0.2

    def __init__(self):
        self.rng = random.Random(0xC0FFEE)
        self.new_table({}, 0, 8)

    def new_table(self, rules, seat, n_players):
        try:
            n = int(n_players) if n_players else 8
        except Exception:
            n = 8
        self.n = max(n, 2)
        self.me = seat
        self.st = {}            # seat -> [decisions, raises, calls]
        self.hand = None
        self.seen = 0
        self.hraise = {}        # this hand: seat -> raises observed
        self.pfr_seat = {}      # this hand: seat -> raised preflop
        self.vol = {}           # this hand: seat -> voluntarily in preflop
        self.i_raised_pf = False
        self.cache = {}

    def hand_end(self, result):
        try:
            if isinstance(result, dict):
                h = result.get('history')
                if h and self.hand is not None:
                    self._absorb(h, 3, self.me)
        except Exception:
            pass
        self.hand = None
        self.seen = 0

    # ------------------------------------------------------------ opponent stats
    def _stat(self, s):
        v = self.st.get(s)
        if v is None:
            v = self.st[s] = [0, 0, 0, 0, 0, 0]
        return v

    def _absorb(self, hist, street, me, sb=-1, bb=-1, blinds=(0, 0)):
        start = self.seen
        if start > len(hist):
            start = 0
        skip = -1
        if start == 0 and street == 0 and hist:
            # leading blind posts (if the engine logs them) are not decisions
            try:
                s0, a0 = hist[0]
                if s0 == sb and a0[0] not in ('fold', 'check') and 0 < int(a0[1] or 0) <= blinds[0]:
                    skip = 0
                    if len(hist) > 1:
                        s1, a1 = hist[1]
                        if s1 == bb and a1[0] not in ('fold', 'check') and 0 < int(a1[1] or 0) <= blinds[1]:
                            skip = 1
                elif s0 == bb and a0[0] not in ('fold', 'check') and 0 < int(a0[1] or 0) <= blinds[1]:
                    skip = 0
            except Exception:
                skip = -1
        for idx in range(start, len(hist)):
            if idx <= skip:
                continue
            try:
                s, a = hist[idx]
                kind = a[0]
            except Exception:
                continue
            if street == 0 and kind == 'raise':
                try:
                    if int(a[1] or 0) <= blinds[1]:
                        continue
                except Exception:
                    pass
            if kind not in ('fold', 'call', 'raise', 'check'):
                continue
            if s == me:
                continue
            v = self._stat(s)
            if kind == 'check':
                continue
            v[0] += 1
            if street == 0:
                v[3] += 1
            if kind == 'raise':
                v[1] += 1
                self.hraise[s] = self.hraise.get(s, 0) + 1
                if street == 0:
                    v[4] += 1
                    self.pfr_seat[s] = True
                    self.vol[s] = True
            elif kind == 'call':
                v[2] += 1
                if street == 0:
                    v[5] += 1
                    self.vol[s] = True
        self.seen = len(hist)

    def agg(self, s):
        v = self.st.get(s)
        if v is None:
            return 0.25
        return (v[1] + 0.25 * 6) / (v[0] + 6.0)

    def pfr(self, s):
        v = self.st.get(s)
        if v is None:
            return 0.15
        return (v[4] + 0.15 * 6) / (v[3] + 6.0)

    def cont(self, s):
        v = self.st.get(s)
        if v is None:
            return 0.3
        return (v[4] + v[5] + 0.3 * 6) / (v[3] + 6.0)

    def raise_frac(self, s):
        a = self.pfr(s)
        f = a * (1.0 + 5.0 * max(0.0, a - 0.15))
        return 0.04 if f < 0.04 else (1.0 if f > 1.0 else f)

    def is_wild(self, s):
        return self.pfr(s) > self.WILD_PFR or self.agg(s) > self.WILD_AGG

    # ------------------------------------------------------------ geometry
    def _geom(self, obs):
        n = len(obs.stacks)
        alive = [i for i in range(n) if obs.stacks[i] > 0 or obs.in_hand[i]]
        b = obs.button
        def nxt(x):
            for d in range(1, n + 1):
                y = (x + d) % n
                if y in alive:
                    return y
            return x
        if len(alive) <= 2:
            sb = b if b in alive else nxt(b)
            bb = nxt(sb)
        else:
            sb = nxt(b); bb = nxt(sb)
        return n, alive, sb, bb

    def _behind(self, obs, n, bb):
        """players still to act behind me up to BB (preflop), able to act."""
        me = obs.seat
        if me == bb:
            return []
        out = []
        x = me
        for _ in range(n):
            x = (x + 1) % n
            if obs.in_hand[x] and obs.stacks[x] > 0:
                out.append(x)
            if x == bb:
                break
        return out

    # ------------------------------------------------------------ main
    def act(self, obs):
        self.t0 = perf_counter()
        try:
            a = self._act(obs)
        except Exception:
            if DEBUG:
                raise
            a = None
        return self._legal(obs, a)

    def _legal(self, obs, a):
        legal = obs.legal
        if not a:
            a = ('check', 0)
        k, amt = a[0], a[1]
        if k == 'raise':
            if 'raise' in legal:
                lo, hi = obs.min_raise, obs.max_raise
                amt = int(amt)
                if amt < lo: amt = lo
                if amt > hi: amt = hi
                return ('raise', int(amt))
            k = 'call'
        if k == 'call':
            if 'call' in legal:
                return ('call', 0)
            k = 'check'
        if k == 'check':
            if 'check' in legal:
                return ('check', 0)
            return ('fold', 0) if 'fold' in legal else ('call', 0)
        if 'check' in legal:
            return ('check', 0)
        if 'fold' in legal:
            return ('fold', 0)
        return ('call', 0) if 'call' in legal else ('check', 0)

    def _act(self, obs):
        if obs.hand_no != self.hand:
            self.hand = obs.hand_no; self.seen = 0
            self.hraise = {}; self.pfr_seat = {}; self.vol = {}
            self.i_raised_pf = False; self.cache = {}
        hist = obs.history or []
        self.me = obs.seat
        if obs.street == 0:
            _, _, sbs, bbs = self._geom(obs)
            self._absorb(hist, 0, obs.seat, sbs, bbs, tuple(obs.blinds))
        else:
            self._absorb(hist, obs.street, obs.seat)
        if obs.street == 0:
            a = self._preflop(obs)
            if a and a[0] == 'raise':
                self.i_raised_pf = True
            return a
        return self._postflop(obs)

    # ------------------------------------------------------------ all-in EV helpers
    def _totals(self, obs):
        return [obs.stacks[i] + obs.bets[i] for i in range(len(obs.stacks))]

    def _ev_fold(self, obs, winner, tax=0.0):
        st = list(obs.stacks)
        pot = obs.pot + sum(obs.bets)
        st[winner] += pot
        if tax > 0 and obs.street == 0:
            # future-game proxy: folding a short stack is not free, the blinds keep coming
            t = int(tax * obs.blinds[1])
            me = obs.seat
            if st[me] > t:
                st[me] -= t
                st[winner] += t
        return icm(obs.seat, st)

    def _ev_showdown(self, obs, opp, eq):
        """I put my whole stack in vs opp (who has or will put in all); others' bets dead."""
        me = obs.seat
        tot = self._totals(obs)
        pot_prev = obs.pot
        c = min(tot[me], tot[opp])
        dead = pot_prev + sum(obs.bets) - obs.bets[me] - obs.bets[opp]
        st = list(obs.stacks)
        stw = list(st); stl = list(st)
        stw[me] = tot[me] + c + dead - 0; stw[opp] = tot[opp] - c
        stl[me] = tot[me] - c; stl[opp] = tot[opp] + c + dead
        # correct bets: st entries excluded current bets; tot included them
        return eq * icm(me, stw) + (1 - eq) * icm(me, stl)

    def _ev_push(self, obs, h, callers, fracs):
        """ICM EV of shoving: callers in order, each calls with top fracs[k]."""
        me = obs.seat
        st = list(obs.stacks)
        pot = obs.pot + sum(obs.bets)
        stf = list(st); stf[me] = st[me] + pot
        reach = 1.0; ev = 0.0
        for k, s in enumerate(callers):
            f = fracs[k]
            if f <= 0: continue
            if f > 1: f = 1.0
            eq = eq_top(h, f)
            ev += reach * f * self._ev_showdown(obs, s, eq)
            reach *= (1 - f)
        ev += reach * icm(me, stf)
        return ev

    # ------------------------------------------------------------ preflop
    def _preflop(self, obs):
        me = obs.seat
        c1, c2 = obs.hole
        h = cls_of(c1, c2)
        r = RANKF[h]
        sb_amt, bb_amt = obs.blinds
        bb_amt = max(bb_amt, 1)
        n, alive, sb, bb = self._geom(obs)
        tot = self._totals(obs)
        my_tot = tot[me]
        others = [i for i in range(n) if i != me and obs.in_hand[i]]
        if not others:
            return ('check', 0)
        max_other = max(tot[i] for i in others)
        eff = min(my_tot, max_other) / float(bb_amt)
        mxbet = max(obs.bets)
        to_call = obs.to_call
        behind = self._behind(obs, n, bb)
        m = len(behind)

        if mxbet <= bb_amt:
            # ---------------- unopened (maybe limpers)
            limpers = [i for i in others if obs.bets[i] >= bb_amt and i != bb and i not in behind]
            if 'check' in obs.legal and to_call == 0:
                # BB option
                if eff <= 15 and limpers:
                    if r <= 0.10:
                        return ('raise', obs.max_raise)
                    return ('check', 0)
                if limpers and r <= 0.07:
                    return ('raise', int(bb_amt * (3 + len(limpers))))
                if r <= 0.03:
                    return ('raise', int(bb_amt * 3.5))
                return ('check', 0)
            if eff <= self.PF_MAX and m >= 1:
                callers = behind + limpers
                fr = self._caller_fracs(obs, m, callers, tot, me, bb_amt, behind)
                evp = self._ev_push(obs, h, callers, fr)
                evf = self._ev_fold(obs, bb, self.FOLD_TAX)
                if evp > evf:
                    return ('raise', obs.max_raise)
                return ('fold', 0)
            thr = OPEN_THR.get(m, 0.11) * self.OPEN_SCALE
            if limpers:
                thr = min(thr, 0.14) * (0.9 if len(limpers) > 1 else 1.0)
            if r <= thr:
                size = bb_amt * (2.5 + len(limpers))
                if m == 1:
                    size = bb_amt * 3
                if size >= 0.33 * my_tot:
                    return ('raise', obs.max_raise)
                return ('raise', int(size))
            if me == sb and to_call <= bb_amt * 0.5 and r <= 0.30 and not limpers:
                return ('call', 0)
            return ('fold', 0)

        # ---------------- facing a raise
        agg_seat = max(others, key=lambda i: obs.bets[i])
        j_allin = obs.stacks[agg_seat] == 0
        nraises = 0
        for (s, a) in hist_iter(obs):
            try:
                if a[0] == 'raise' and int(a[1] or 0) > bb_amt:
                    nraises += 1
            except Exception:
                pass
        fj = self.raise_frac(agg_seat)
        jt = tot[agg_seat]
        sj = min(jt, my_tot) / float(bb_amt)
        big = obs.bets[agg_seat] >= 0.4 * jt or j_allin
        if big:
            # shove-ish: estimate its range vs equilibrium push fraction
            mj = 3
            pf, _ = pf_lookup(mj, sj)
            fj = max(fj, pf * (0.7 if nraises >= 2 else 1.0))
            if self.is_wild(agg_seat):
                fj = max(fj, 0.8)
        elif self.i_raised_pf:
            fj = fj * 0.55
        fj = min(1.0, max(0.025, fj))
        # live players behind me who could still wake up
        n_behind_live = len([i for i in behind if i != agg_seat])
        commit = to_call >= 0.4 * obs.stacks[me] or j_allin or eff <= 18
        if commit:
            eq = eq_top(h, fj)
            if n_behind_live:
                eq *= (1.0 - 0.025 * n_behind_live)
            evf = self._ev_fold(obs, agg_seat, self.FOLD_TAX)
            if j_allin or to_call >= obs.stacks[me] or 'raise' not in obs.legal:
                evc = self._ev_showdown(obs, agg_seat, eq)
                return ('call', 0) if evc > evf else ('fold', 0)
            # re-shove: opponent calls with a tighter part of its range
            fcall = fj * (0.45 if not self.is_wild(agg_seat) else 0.9)
            pcall = min(1.0, fcall / fj)
            eqc = eq_top(h, max(0.02, fcall))
            st = list(obs.stacks); pot = obs.pot + sum(obs.bets); st[me] += pot
            evs = (1 - pcall) * icm(me, st) + pcall * self._ev_showdown(obs, agg_seat, eqc)
            # flat-call when the price is tiny is folded into the shove decision for simplicity
            if evs > evf:
                return ('raise', obs.max_raise)
            if to_call <= 0.08 * obs.stacks[me] and r <= 0.25:
                return ('call', 0)
            return ('fold', 0)
        # deep stacks
        if self.i_raised_pf or nraises >= 2:
            if r <= 0.021:
                return ('raise', obs.max_raise if eff <= 60 else int(obs.bets[agg_seat] * 2.4))
            if r <= 0.05 and to_call <= 0.22 * obs.stacks[me]:
                return ('call', 0)
            return ('fold', 0)
        three = min(0.07, max(0.022, 0.3 * fj))
        callt = min(0.30, max(0.05, self.CALL_SCALE * fj))
        if me == bb and to_call <= 2.2 * bb_amt:
            callt = max(callt, 0.33)
        if r <= three:
            size = 3 * obs.bets[agg_seat] + (obs.pot + sum(obs.bets) - obs.bets[agg_seat])
            if size >= 0.33 * my_tot:
                return ('raise', obs.max_raise)
            return ('raise', int(size))
        if r <= callt and to_call <= 0.12 * obs.stacks[me]:
            return ('call', 0)
        return ('fold', 0)

    def _fold_stacks(self, obs, bb):
        st = list(obs.stacks)
        st[bb] += obs.pot + sum(obs.bets)
        return st

    def _caller_fracs(self, obs, m, callers, tot, me, bb_amt, behind):
        fr = []
        for k, s in enumerate(callers):
            S = min(tot[me], tot[s]) / float(bb_amt)
            _, cf = pf_lookup(m, S)
            if k < len(cf):
                f = cf[k]
            else:
                f = 0.25
            v = self.st.get(s)
            if v is not None and v[3] >= 6:
                f = 0.5 * f + 0.5 * min(1.0, self.cont(s) * 0.9)
            if self.is_wild(s):
                f = max(f, 0.6)
            fr.append(f)
        return fr

    # ------------------------------------------------------------ postflop
    def _opp_frac(self, s):
        if self.is_wild(s):
            return 1.0
        if self.pfr_seat.get(s):
            f = self.raise_frac(s)
        elif self.vol.get(s):
            f = min(1.0, max(self.raise_frac(s) * 2.5, self.cont(s) * 1.1))
        else:
            f = 0.85
        nr = self.hraise.get(s, 0) - (1 if self.pfr_seat.get(s) else 0)
        for _ in range(max(0, nr)):
            f *= 0.65
        return max(0.03, f)

    def _equity(self, obs, opps):
        hole = obs.hole; board = tuple(obs.board)
        fr = tuple(round(self._opp_frac(s), 2) for s in opps[:3])
        reqs = []
        for s in opps[:3]:
            q = 0
            if self.COND and not self.is_wild(s):
                bs = obs.bets[s]
                if bs > 0:
                    q = 2 if (bs >= 0.75 * max(1, obs.pot) or obs.stacks[s] == 0) else 1
            reqs.append(q)
        reqs = tuple(reqs)
        key = (board, fr, reqs)
        rec = self.cache.get(key)
        if rec is None:
            base = self.cache.get(board)
            if base is None:
                dead = set(hole) | set(board)
                flt = [t for t in COMBOS if t[0] not in dead and t[1] not in dead]
                base = (flt, [RANKF[t[2]] for t in flt], [c for c in range(52) if c not in dead])
                self.cache[board] = base
            flt, rfl, deck = base
            lists = []
            for f in fr:
                hi = bisect_left(rfl, f + 1e-9)
                if hi < 30: hi = min(len(flt), 30)
                lists.append(flt[:hi])
            bcnt = {}
            for c in board:
                bcnt[c >> 2] = bcnt.get(c >> 2, 0) + 1
            mxc = max(bcnt.values()) if bcnt else 1
            npr = sum(1 for v in bcnt.values() if v >= 2)
            bc = 3 if mxc >= 3 else (2 if npr >= 2 else (1 if npr == 1 else 0))
            thr = tuple((max(q, bc + 1) if q else 0) for q in reqs)
            rec = [0.0, 0, lists, deck, thr]
            self.cache[key] = rec
        lists, deck, thr = rec[2], rec[3], rec[4]
        rnd = self.rng.random
        keep = self.COND_KEEP
        need = 5 - len(board)
        rng = self.rng
        hl = list(hole) + list(board)
        bl = list(board)
        deadline = self.t0 + self.MC_BUDGET
        wins = rec[0]; n = rec[1]; it = 0
        choice = rng.choice; sample = rng.sample
        while it < 400:
            if (it >= 4 or n >= 4) and perf_counter() > deadline:
                break
            it += 1
            used = set()
            hands = []
            ok = True
            for oi, L in enumerate(lists):
                if not L:
                    ok = False; break
                q = thr[oi]
                last = None
                for _ in range(5):
                    t = choice(L)
                    if t[0] in used or t[1] in used:
                        continue
                    last = t
                    if not q or (evaluate([t[0], t[1]] + bl) >> 20) >= q or rnd() < keep:
                        break
                t = last
                if t is None:
                    ok = False
                if not ok: break
                used.add(t[0]); used.add(t[1]); hands.append(t)
            if not ok:
                continue
            if need:
                run = [c for c in sample(deck, need + 6) if c not in used][:need]
                if len(run) < need:
                    continue
                mine = evaluate(hl + run)
                bd = bl + run
            else:
                mine = evaluate(hl)
                bd = bl
            best = 0; ties = 0
            for t in hands:
                v = evaluate([t[0], t[1]] + bd)
                if v > best: best = v
            if mine > best: wins += 1.0
            elif mine == best: wins += 0.5
            n += 1
        rec[0] = wins; rec[1] = n
        eq = wins / n if n else 0.4
        extra = len(opps) - 3
        if extra > 0:
            eq *= 0.85 ** extra
        return eq, n

    def _postflop(self, obs):
        me = obs.seat
        opps = [i for i in range(len(obs.stacks)) if i != me and obs.in_hand[i]]
        if not opps:
            return ('check', 0)
        # aggressor first
        opps.sort(key=lambda i: -obs.bets[i])
        eq, nsamp = self._equity(obs, opps)
        se = (eq * (1 - eq) / max(1, nsamp)) ** 0.5
        pot = obs.pot + sum(obs.bets)
        to_call = obs.to_call
        my_stack = obs.stacks[me]
        bb_amt = max(obs.blinds[1], 1)
        live = [i for i in opps if obs.stacks[i] > 0]
        sticky = all(self.cont(i) > 0.55 for i in opps)
        if to_call <= 0:
            vthr = self.VTHR_STICKY if sticky else self.VTHR
            if eq > vthr and live:
                size = obs.bets[me] + int(pot * (0.9 if sticky else 0.7))
                if my_stack <= pot * 1.1:
                    return ('raise', obs.max_raise)
                return ('raise', size)
            if (self.i_raised_pf and obs.street == 1 and len(opps) <= 2 and eq > 0.30 and live and not sticky
                    and self.rng.random() < self.CBET):
                return ('raise', obs.bets[me] + int(pot * 0.5))
            return ('check', 0)
        agg_seat = opps[0]
        price = to_call / float(pot + to_call)
        allin_spot = to_call >= 0.45 * my_stack or obs.stacks[agg_seat] == 0
        if eq - self.LCB * se > self.RAISE_EQ and 'raise' in obs.legal and live:
            mx = max(obs.bets)
            size = 3 * mx + (pot - sum(obs.bets))
            if size >= 0.4 * (my_stack + obs.bets[me]):
                return ('raise', obs.max_raise)
            return ('raise', int(size))
        if allin_spot:
            evf = self._ev_fold(obs, agg_seat)
            evc = self._ev_showdown(obs, agg_seat, eq)
            return ('call', 0) if evc > evf else ('fold', 0)
        margin = self.MARGIN if obs.street < 3 else self.MARGIN + 0.02
        if eq >= price + margin:
            return ('call', 0)
        return ('fold', 0)


def hist_iter(obs):
    h = obs.history or []
    for x in h:
        try:
            s, a = x
            yield s, a
        except Exception:
            continue


try:
    import gc as _gc
    _gc.collect()
    _gc.freeze()
except Exception:
    pass
