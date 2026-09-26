const charts = ['ecp-endpoint', 'ecp-directory', 'ecp-broker', 'eccosp-artemis'];
const chart = process.env.CHART;

if (!charts.includes(chart)) {
  throw new Error('CHART must name one standalone chart');
}

module.exports = {
  branches: ['main'],
  tagFormat: `${chart}-\${version}`,
  plugins: [
    ['./.github/scripts/chart_release.cjs', { chart }],
    ['@semantic-release/exec', {
      prepareCmd: `python .github/scripts/bump_chart_version.py ${chart} \${nextRelease.version} && python .github/scripts/validate_charts.py --chart ${chart}`,
    }],
    ['@semantic-release/git', {
      assets: [`charts/${chart}/Chart.yaml`],
      message: `chore(release): ${chart} \${nextRelease.version} [skip ci]\n\n\${nextRelease.notes}`,
    }],
    ['@semantic-release/github', {
      assets: [{ path: `.ci-artifacts/${chart}/publish/${chart}-*.tgz`, label: `${chart} Helm chart` }],
      releaseNameTemplate: '<%= nextRelease.gitTag %>',
      successComment: false,
      failComment: false,
      releasedLabels: false,
      labels: false,
    }],
  ],
};