const { execFileSync } = require('node:child_process');

function chartCommits(chart, commits) {
  return commits.filter((commit) => {
    const files = execFileSync('git', [
      'show', '--first-parent', '--format=', '--name-only', commit.hash,
    ], { encoding: 'utf8' }).trim().split('\n');
    return files.some((file) => file.startsWith(`charts/${chart}/`));
  });
}

function releaseType(commit) {
  const subject = commit.message.split('\n')[0];
  const match = /^([a-z]+)(?:\([^)]+\))?(!)?:\s+(.+)/.exec(subject);
  if (/(?:^|\n)BREAKING CHANGE:\s+/m.test(commit.message)) return 'major';
  if (!match) return 'patch';
  if (match[2]) return 'major';
  if (match[1] === 'feat') return 'minor';
  return 'patch';
}

exports.analyzeCommits = async ({ chart }, { commits, logger }) => {
  const order = { patch: 1, minor: 2, major: 3 };
  const relevant = chartCommits(chart, commits);
  const type = relevant.map(releaseType).reduce((highest, current) =>
    order[current] > (order[highest] || 0) ? current : highest, null);
  logger.log('%s: %d changed commits; release: %s', chart, relevant.length, type || 'none');
  return type;
};

exports.generateNotes = async ({ chart }, { commits, nextRelease }) => {
  const relevant = chartCommits(chart, commits);
  return [`## ${chart} ${nextRelease.version}`, '', ...relevant.map((commit) =>
    `- ${commit.message.split('\n')[0]} (${commit.hash.slice(0, 7)})`)].join('\n');
};