# How to Extract Your Advent of Code Session Cookie

## Quick Method: Browser Console (Recommended)

This is the fastest and easiest method:

1. **Log in** to https://adventofcode.com in your browser
2. **Press F12** to open Developer Tools
3. **Go to the Console tab**
4. **Paste this command** and press Enter:

```javascript
document.cookie.split('; ').find(c => c.startsWith('session=')).split('=')[1]
```

5. **Copy the output** (the long hexadecimal string)
6. **Set the environment variable**:

```bash
export AOC_SESSION='<paste_the_value_here>'
```

---

## Method 2: Developer Tools UI

### Chrome / Edge / Brave

1. **Log in** to https://adventofcode.com
2. **Press F12** (or `Ctrl+Shift+I` / `Cmd+Option+I`)
3. Click the **Application** tab
4. In the left sidebar, expand **Cookies**
5. Click on `https://adventofcode.com`
6. Find the cookie named **session**
7. **Double-click the Value** and copy it
8. Set the environment variable:

```bash
export AOC_SESSION='<paste_the_value_here>'
```

### Firefox

1. **Log in** to https://adventofcode.com
2. **Press F12** (or `Ctrl+Shift+I` / `Cmd+Option+I`)
3. Click the **Storage** tab
4. Expand **Cookies**
5. Click on `https://adventofcode.com`
6. Find the cookie named **session**
7. **Double-click the Value** and copy it
8. Set the environment variable:

```bash
export AOC_SESSION='<paste_the_value_here>'
```

---

## Method 3: Automatic Extraction (Advanced)

We provide a Python script that can automatically extract the cookie from your browser's cookie database:

```bash
python extract_cookie_from_browser.py
```

**Note:** This script may require:
- The browser to be closed (to unlock the database)
- Additional dependencies for decryption on some systems
- Permissions to access browser data directories

---

## Making the Cookie Persistent

To avoid setting the environment variable every time, add it to your shell configuration:

### Bash
```bash
echo "export AOC_SESSION='your_cookie_value'" >> ~/.bashrc
source ~/.bashrc
```

### Zsh
```bash
echo "export AOC_SESSION='your_cookie_value'" >> ~/.zshrc
source ~/.zshrc
```

### Fish
```bash
set -Ux AOC_SESSION 'your_cookie_value'
```

---

## Verifying the Cookie

After setting the environment variable, verify it's working:

```bash
# Check if it's set
echo $AOC_SESSION

# Test the client
python test_client.py
```

---

## Security Notes

- **Keep your session token private** - treat it like a password
- **Don't commit it to git** - add `.env` files to `.gitignore`
- **The token doesn't expire** unless you log out or clear browser cookies
- **Works with 2FA** since you authenticate in the browser first
