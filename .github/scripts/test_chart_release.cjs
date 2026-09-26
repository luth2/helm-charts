const assert = require('node:assert/strict');
const { execFileSync } = require('node:child_process');
const { mkdtempSync, mkdirSync, rmSync, writeFileSync } = require('node:fs');
const { tmpdir } = require('node:os');
const { join } = require('node:path');
const { test } = require('node:test');
const plugin = require('./chart_release.cjs');

test('all changes to the selected chart create a release', async () => {
  const directory = mkdtempSync(join(tmpdir(), 'chart-release-'));
  const previous = process.cwd();
  const commits = [];
  try {
    process.chdir(directory);
    const git = (...args) => execFileSync('git', args, {
      encoding: 'utf8',
      env: { ...process.env, GIT_AUTHOR_NAME: 'CI', GIT_AUTHOR_EMAIL: 'ci@example.test',
        GIT_COMMITTER_NAME: 'CI', GIT_COMMITTER_EMAIL: 'ci@example.test' },
    }).trim();
    git('init', '-q');
    for (const [chart, message] of [
      ['ecp-broker', 'feat: broker feature'],
      ['ecp-endpoint', 'fix: endpoint correction'],
      ['ecp-endpoint', 'feat!: endpoint contract changed'],
      ['ecp-endpoint', 'docs: endpoint guide'],
      ['ecp-directory', 'refactor!: directory contract changed'],
      ['eccosp-artemis', 'update chart documentation'],
      ['ecp-directory', 'adjust directory API\n\nBREAKING CHANGE: old API removed'],
    ]) {
      const chartDirectory = join(directory, 'charts', chart);
      mkdirSync(chartDirectory, { recursive: true });
      writeFileSync(join(chartDirectory, 'Chart.yaml'), message);
      git('add', '.');
      git('commit', '-qm', message);
      commits.push({ hash: git('rev-parse', 'HEAD'), message });
    }
    const logger = { log() {} };
    assert.equal(await plugin.analyzeCommits({ chart: 'ecp-endpoint' }, { commits, logger }), 'major');
    assert.equal(await plugin.analyzeCommits({ chart: 'ecp-broker' }, { commits, logger }), 'minor');
    assert.equal(await plugin.analyzeCommits({ chart: 'ecp-directory' }, { commits, logger }), 'major');
    assert.equal(await plugin.analyzeCommits({ chart: 'eccosp-artemis' }, { commits, logger }), 'patch');
    assert.equal(await plugin.analyzeCommits({ chart: 'ecp-endpoint' }, { commits: [commits[3]], logger }), 'patch');
    assert.equal(await plugin.analyzeCommits({ chart: 'ecp-directory' }, { commits: [commits[6]], logger }), 'major');
    assert.equal(await plugin.analyzeCommits({ chart: 'ecp-endpoint' }, { commits: [commits[0]], logger }), null);
    const notes = await plugin.generateNotes({ chart: 'ecp-endpoint' },
      { commits, nextRelease: { version: '6.0.0' } });
    assert.match(notes, /endpoint correction/);
    assert.match(notes, /endpoint guide/);
    assert.doesNotMatch(notes, /broker feature|update chart documentation/);
  } finally {
    process.chdir(previous);
    rmSync(directory, { recursive: true, force: true });
  }
});