#!/usr/bin/env python3
"""Fix corrupt unified diff patches: recalculate hunk line counts.
Only fixes patches 0082-0101 (the S9 series that was ported to A70)."""
import re, sys, glob, os

def fix_patch(path):
    try:
        with open(path, encoding='utf-8', errors='replace') as f:
            lines = f.readlines()
    except Exception as e:
        print(f"  SKIP {os.path.basename(path)}: {e}")
        return False

    fixed = []
    i = 0
    changed = False
    while i < len(lines):
        line = lines[i]
        m = re.match(r'^(@@ -(\d+),(\d+) \+(\d+),(\d+) @@(.*))\n$', line)
        if not m:
            fixed.append(line)
            i += 1
            continue

        old_start = int(m.group(2))
        old_count_claimed = int(m.group(3))
        new_start = int(m.group(4))
        new_count_claimed = int(m.group(5))
        tail = m.group(6)

        # Collect hunk body lines
        j = i + 1
        ctx = 0
        add = 0
        rem = 0
        while j < len(lines):
            l = lines[j]
            if l.startswith('diff --git') or l.startswith('@@'):
                break
            if l.startswith('index ') or l.startswith('--- ') or l.startswith('+++ '):
                break
            if l.startswith('+'):
                add += 1
            elif l.startswith('-'):
                rem += 1
            elif l.startswith(' ') or l == '\n':
                ctx += 1
            else:
                # Could be "\ No newline at end of file" - skip
                if l.startswith('\\'):
                    j += 1
                    continue
                break
            j += 1

        old_actual = ctx + rem
        new_actual = ctx + add

        if old_actual != old_count_claimed or new_actual != new_count_claimed:
            new_header = f"@@ -{old_start},{old_actual} +{new_start},{new_actual} @@{tail}\n"
            fixed.append(new_header)
            changed = True
            print(f"  {os.path.basename(path)} line {i+1}: "
                  f"-{old_start},{old_count_claimed} +{new_start},{new_count_claimed} -> "
                  f"-{old_start},{old_actual} +{new_start},{new_actual}")
        else:
            fixed.append(line)
        i += 1

    if changed:
        with open(path, 'w', newline='\n') as f:
            f.writelines(fixed)
    return changed

# Only fix the S9 patches (0082-0101) that were ported
patches = sorted(glob.glob('xnu/patches/008*.patch') +
                 glob.glob('xnu/patches/009*.patch') +
                 glob.glob('xnu/patches/010*.patch'))
total_fixed = 0
for p in patches:
    if fix_patch(p):
        total_fixed += 1

print(f"\nFixed {total_fixed} patch file(s)")
