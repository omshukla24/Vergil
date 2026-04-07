import os

filepath = 'c:/Users/user/Desktop/auth0/archon-project/dashboard/index.html'

with open(filepath, 'r', encoding='utf-8') as f:
    text = f.read()

# The missing script closing tag is right after `tailwind.config = { ... }` which is at line 112.
# We will find `            }\n        }\n    \n    // --- Advanced UX & Routing ---`
# and replace it to add `</script>`
target = "            }\n        }\n    \n    // --- Advanced UX & Routing ---"
if target in text:
    print("Found target 1!")
    # BUT wait, we want to delete perfectly from `// --- Advanced UX & Routing ---`
    # all the way to the First `</script>` closing tag that we accidentally appended!
    # Let's find index.
    start_idx = text.find("    // --- Advanced UX & Routing ---")
    end_idx = text.find("</script>", start_idx) + len("</script>")
    
    # We remove this entire duplicated chunk, and replace with just `</script>`!
    new_text = text[:start_idx] + "</script>" + text[end_idx:]
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(new_text)
    print("Fixed!")
else:
    print("Target not found.")
