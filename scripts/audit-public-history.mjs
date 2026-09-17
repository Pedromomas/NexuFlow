import { execFileSync } from 'node:child_process';
const git = (...args) => execFileSync('git',args,{maxBuffer:256*1024*1024});
const objects = git('rev-list','--objects','--all').toString().trim().split('\n');
const checks = [
  ['private-key',/-----BEGIN (?:RSA |EC |OPENSSH |ENCRYPTED )?PRIVATE KEY-----/],
  ['github-token',/\b(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{40,})\b/],
  ['aws-key',/\bAKIA[0-9A-Z]{16}\b/],
  ['firebase-private-key',/"private_key"\s*:\s*"[^"\r\n]{60,}/],
  ['payment-token',/\bAPP_USR-[A-Za-z0-9-]{30,}\b/],
];
let scanned = 0; const findings = [];
for (const line of objects) {
  const [oid,...path] = line.split(' ');
  if (git('cat-file','-t',oid).toString().trim() !== 'blob') continue;
  const blob = git('cat-file','blob',oid);
  if (blob.includes(0)) continue;
  scanned++; const text = blob.toString('utf8');
  for (const [kind,pattern] of checks) if (pattern.test(text)) findings.push({kind,oid,path:path.join(' ')});
}
// Never print matched credentials. Findings contain paths/object identifiers only.
console.log(JSON.stringify({scannedTextBlobs:scanned,findings},null,2));
if (findings.length) process.exitCode=1;
