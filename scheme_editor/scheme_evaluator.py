import logging
import re
from pathlib import Path

logging.basicConfig(level=logging.DEBUG, format='[%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

SUPPRESS_LOGGING = False


class SchemeEvaluator:
    TOKEN_RE = re.compile(r'%([a-zA-Z0-9_]+)%')
    FUNC_RE = re.compile(r'\$(\w+)\((.*?)\)')

    def __init__(self, metadata):
        # Copy metadata to avoid mutating original
        self.metadata = dict(metadata)
        # Inject currentfoldername if possible
        self._inject_currentfoldername()

    def _inject_currentfoldername(self):
        """
        If metadata contains a 'current_folder' key with a path,
        extract the last folder name and set 'currentfoldername' token.
        """
        folder_path = self.metadata.get("current_folder", "")
        if folder_path:
            # Normalize path and get last folder name
            folder_name = Path(folder_path).name
            self.metadata["currentfoldername"] = folder_name
        else:
            # Ensure token exists as empty string if no current_folder key
            self.metadata.setdefault("currentfoldername", "")

    def eval(self, text):
        for _ in range(20):
            new = self._eval_once(text)
            if new == text:
                break
            text = new
        return text

    def _eval_once(self, text):
        def token_repl(m):
            token = m.group(1)
            # Handle numbered tokens like formatN2, additionalN3, sourceN4 etc.
            m2 = re.match(r'^(format|additional|source)(N(\d+))?$', token)
            if m2:
                base = m2.group(1)
                n_part = m2.group(2)  # like 'N3' or None
                n_num_str = m2.group(3)  # '3' or None
                values = self.metadata.get(base + "N", [])
                if isinstance(values, str):
                    values = [values]
                if n_part is None:
                    # %format% etc.
                    return self.metadata.get(base, "")
                elif n_num_str is None:
                    # %formatN%
                    return ", ".join(values)
                else:
                    # %formatN2%
                    idx = int(n_num_str) - 1
                    return values[idx] if 0 <= idx < len(values) else ""
            else:
                val = self.metadata.get(token, "")
                if isinstance(val, list):
                    return ", ".join(val)
                return val

        def func_repl(m):
            fname, fargs = m.group(1), m.group(2)
            args = self._split_args(fargs)
            args = [self.eval(arg) for arg in args]
            return self._apply_func(fname, args)

        text = self.TOKEN_RE.sub(token_repl, text)
        text = self.FUNC_RE.sub(func_repl, text)
        return text

    def _split_args(self, argstr):
        args, current, depth, i = [], [], 0, 0
        while i < len(argstr):
            c = argstr[i]
            if c == ',' and depth == 0:
                args.append(''.join(current).strip())
                current = []
            else:
                if c == '(':
                    depth += 1
                elif c == ')':
                    depth -= 1
                current.append(c)
            i += 1
        if current:
            args.append(''.join(current).strip())
        return args

    def _apply_func(self, fname, args):
        def to_num(x): return float(x) if x.replace('.', '', 1).isdigit() else 0.0
        def to_bool(x): return x == "1"
        if fname == "upper" and len(args) == 1: return args[0].upper()
        if fname == "lower" and len(args) == 1: return args[0].lower()
        if fname == "title" and len(args) == 1: return args[0].title()
        if fname == "substr" and (2 <= len(args) <= 3):
            s, start = args[0], int(args[1])
            return s[start:int(args[2])] if len(args) == 3 else s[start:]
        if fname == "left" and len(args) == 2: return args[0][:int(args[1])]
        if fname == "right" and len(args) == 2: return args[0][-int(args[1]):]
        if fname == "replace" and len(args) == 3: return args[0].replace(args[1], args[2])
        if fname == "len" and len(args) == 1: return str(len(args[0]))
        if fname == "pad" and (2 <= len(args) <= 3):
            s, n, ch = args[0], int(args[1]), (args[2] if len(args) == 3 else " ")[0]
            return s.ljust(n, ch) if len(s) < n else s[:n]
        if fname == "add" and len(args) == 2: return str(to_num(args[0]) + to_num(args[1]))
        if fname == "sub" and len(args) == 2: return str(to_num(args[0]) - to_num(args[1]))
        if fname == "mul" and len(args) == 2: return str(to_num(args[0]) * to_num(args[1]))
        if fname == "div" and len(args) == 2:
            denom = to_num(args[1])
            return str(to_num(args[0]) / denom) if denom != 0 else "0"
        if fname == "eq" and len(args) == 2: return "1" if args[0] == args[1] else "0"
        if fname == "lt" and len(args) == 2: return "1" if to_num(args[0]) < to_num(args[1]) else "0"
        if fname == "gt" and len(args) == 2: return "1" if to_num(args[0]) > to_num(args[1]) else "0"
        if fname == "and": return "1" if all(to_bool(a) for a in args) else "0"
        if fname == "or": return "1" if any(to_bool(a) for a in args) else "0"
        if fname == "not" and len(args) == 1: return "1" if not to_bool(args[0]) else "0"
        if fname == "datetime" and len(args) == 0: return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if fname == "year" and len(args) == 1: return args[0][:4]
        if fname == "month" and len(args) == 1: return args[0][5:7]
        if fname == "day" and len(args) == 1: return args[0][8:10]
        if fname == "if" and len(args) == 3: return args[1] if args[0] == "1" else args[2]
        if fname == "if2" and len(args) >= 2:
            for val in args[:-1]:
                if val: return val
            return args[-1]
        return ""

TOKENS = [
    "%artist%", "%date%", "%venue%", "%city%", "%format%", "%additional%", "%source%", "%foldername%", "%currentfoldername%",
    "%formatN%", "%formatN2%", "%formatN3%", "%formatN4%", "%formatN5%",
    "%additionalN%", "%additionalN2%", "%additionalN3%", "%additionalN4%", "%additionalN5%",
    "%sourceN%", "%sourceN2%", "%sourceN3%", "%sourceN4%", "%sourceN5%",
    "$upper(text)", "$lower(text)", "$title(text)", "$substr(text,start[,end])",
    "$left(text,n)", "$right(text,n)", "$replace(text,search,replace)",
    "$len(text)", "$pad(text,n,ch)", "$add(x,y)", "$sub(x,y)", "$mul(x,y)",
    "$div(x,y)", "$eq(x,y)", "$lt(x,y)", "$gt(x,y)", "$and(x,y,…)", "$or(x,y,…)",
    "$not(x)", "$datetime()", "$year(date)", "$month(date)", "$day(date)",
    "$if(cond,T,F)", "$if2(v1,v2,…,fallback)",
]


SAMPLE_METADATA = {
    "artist": "Phish", "venue": "Madison Square Garden", "city": "New York, NY",
    "date": "1995-12-31", "source": "SBD", "format": "FLAC24", "additional": "NYE95",
    "formatN": ["FLAC24", "MP3_320"], "additionalN": ["NYE95", "Remastered"],
    "sourceN": ["SBD", "Audience"], "year": "1995",
    "current_folder": "ph1995-12-31 - Madison Square Garden - New York, NY"  # Example current folder path for demo
}
