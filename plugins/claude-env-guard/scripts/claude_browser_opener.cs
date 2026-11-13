// Compile with built-in Windows .NET compiler (no external toolchain required):
// C:\Windows\Microsoft.NET\Framework64\v4.0.30319\csc.exe /target:winexe /nologo /out:claude-browser-opener.exe claude_browser_opener.cs

using System;
using System.Diagnostics;
using System.IO;

static class Program
{
    private static string CleanArg(string value)
    {
        if (string.IsNullOrEmpty(value)) return "";
        return value.Replace("\"", "").Replace("\r", "").Replace("\n", "").TrimEnd('\\');
    }

    [STAThread]
    static int Main(string[] args)
    {
        if (args.Length < 1 || string.IsNullOrEmpty(args[0]))
            return 1;

        string url = args[0].Trim();
        if (url.IndexOf('"') >= 0 || url.IndexOf('\r') >= 0 || url.IndexOf('\n') >= 0)
            return 1;

        if (!url.StartsWith("https://", StringComparison.OrdinalIgnoreCase) &&
            !url.StartsWith("http://", StringComparison.OrdinalIgnoreCase))
            return 1;

        string chrome = Environment.GetEnvironmentVariable("CLAUDE_GUARD_CHROME");
        if (string.IsNullOrWhiteSpace(chrome))
            chrome = @"C:\Program Files\Google\Chrome\Application\chrome.exe";
        if (!File.Exists(chrome))
            return 1;

        string profile = Environment.GetEnvironmentVariable("CLAUDE_GUARD_PROFILE");
        if (string.IsNullOrWhiteSpace(profile))
        {
            string home = Environment.GetFolderPath(Environment.SpecialFolder.UserProfile);
            profile = Path.Combine(home, ".claude-chrome-profile");
        }
        profile = CleanArg(profile);

        string proxy = Environment.GetEnvironmentVariable("CLAUDE_GUARD_PROXY");
        if (string.IsNullOrWhiteSpace(proxy))
            proxy = "http://127.0.0.1:7897";
        proxy = CleanArg(proxy);

        try
        {
            Directory.CreateDirectory(profile);
            var psi = new ProcessStartInfo
            {
                FileName = chrome,
                Arguments = string.Format(
                    "\"--user-data-dir={0}\" \"--proxy-server={1}\" --lang=en-US --force-webrtc-ip-handling-policy=disable_non_proxied_udp --enforce-webrtc-ip-permission-check --no-first-run \"{2}\"",
                    profile, proxy, url
                ),
                UseShellExecute = false,
                CreateNoWindow = true
            };
            Process.Start(psi);
            return 0;
        }
        catch
        {
            return 1;
        }
    }
}
