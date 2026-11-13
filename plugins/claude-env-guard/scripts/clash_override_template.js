// Clash Verge Rev / Mihomo Override Script Template for Claude Anti-Risk-Control
// Customize TARGET_NODE below if you want a specific node placed at the top of the group.

function main(config, profileName) {
  const TARGET_NODE = "__TARGET_NODE__"; // Replace with preferred node name or leave empty
  const claudeGroupName = "🔒 Claude-固定出口";

  // 1. Filter out banned regions (CN, HK, MO) and info/traffic indicator nodes
  const excludeRegex = /香港|HK|Hong\s*Kong|澳门|MO|Macau|中国|CN|China|内地|回国|剩余|到期|订阅|官网|重置|流量|套餐/i;
  const allProxies = (config.proxies || [])
    .map(p => (p && p.name ? p.name : ""))
    .filter(Boolean);
  let validProxies = allProxies.filter(name => !excludeRegex.test(name));

  // If a target node is specified and exists, move it to index 0 so 'select' defaults to it
  if (TARGET_NODE && TARGET_NODE !== "__TARGET_NODE__" && (validProxies.includes(TARGET_NODE) || allProxies.includes(TARGET_NODE))) {
    validProxies = [TARGET_NODE, ...validProxies.filter(n => n !== TARGET_NODE)];
  }

  // 2. Create static 'select' group (never use url-test or load-balance for Claude)
  const claudeGroup = {
    name: claudeGroupName,
    type: "select",
    proxies: validProxies.length > 0 ? validProxies : ["DIRECT"]
  };

  config["proxy-groups"] = config["proxy-groups"] || [];
  // Remove existing group with same name if present
  config["proxy-groups"] = config["proxy-groups"].filter(g => g && g.name !== claudeGroupName);
  config["proxy-groups"].unshift(claudeGroup);

  // 3. Pin all Anthropic, Persona KYC, Stripe, and Telemetry domains to the same exit IP
  const claudeDomains = [
    // Core Claude & Anthropic domains
    "anthropic.com",
    "claude.ai",
    "claude.com",
    "claudeusercontent.com",
    // Persona KYC identity verification (must share the exact same exit IP)
    "withpersona.com",
    "persona.com",
    // Payment & anti-bot challenge domains
    "stripe.com",
    "stripe.network",
    "hcaptcha.com",
    "challenges.cloudflare.com",
    "arkoselabs.com",
    "funcaptcha.com",
    // Telemetry, feature flags & support widgets (prevent direct domestic leak)
    "statsig.com",
    "statsigapi.net",
    "growthbook.io",
    "sentry.io",
    "intercom.io",
    "intercomcdn.com",
    "segment.io"
  ];

  const claudeRules = claudeDomains.map(domain => `DOMAIN-SUFFIX,${domain},${claudeGroupName}`);
  const claudeRuleSet = new Set(claudeRules);
  const existingRules = (config.rules || []).filter(r => !claudeRuleSet.has(r));

  // Prepend rules idempotently at highest priority
  config.rules = [...claudeRules, ...existingRules];

  // 4. Harden DNS against domestic DNS poisoning and leaks
  config.dns = config.dns || {};
  config.dns["enable"] = true;
  config.dns["respect-rules"] = true;
  if (!config.dns["enhanced-mode"]) {
    config.dns["enhanced-mode"] = "fake-ip";
  }

  return config;
}
