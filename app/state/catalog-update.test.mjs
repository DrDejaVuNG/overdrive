import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {register} from 'node:module';
import test from 'node:test';

register(new URL('./download-queue-test-loader.mjs', import.meta.url), import.meta.url);
const {applyUpdate, valid} = await import('./catalog-update.js');

const line = (id, extra = {}) => ({
  id, title: 'Demo ' + id, platform: id.startsWith('PPSA') ? 'ps5' : 'ps4', providers: ['vikingfile'], direct: false,
  developer: '', publisher: '', releaseDate: '2026-10-21', genres: ['Action'], features: [], recommendations: 0,
  art: {cover: 'https://example.com/c.png', tint: '#112233'}, added: '2026-10-21', source: 'superpsx', ...extra,
});
const update = (extra = {}) => ({
  format: 1, version: '1.0.9', base: 'abc', generated: '2026-10-22T02:00:00Z',
  games: [{block: 'games', line: line('CUSA00001')}, {block: 'twins', line: line('PPSA00002', {work: 7})}],
  removed: ['CUSA00009'],
  releases: {CUSA00001: [{id: 'r1', filename: 'CUSA00001-game-1-r1.pkg', format: 'pkg', url: 'https://example.com'}], CUSA00003: null},
  pages: {CUSA00001: {about: ['Text'], shots: [], summary: ''}},
  ...extra,
});

test('a well-formed update passes its checks', () => {
  assert.equal(valid(update()), true);
});

test('an update a screen could trip on is refused', () => {
  const broken = [
    update({format: 2}),
    update({games: [{block: 'games', line: line('CUSA00001', {releaseDate: null})}]}),
    update({games: [{block: 'games', line: line('CUSA00001', {genres: 'Action'})}]}),
    update({games: [{block: 'menu', line: line('CUSA00001')}]}),
    update({games: [{block: 'games', line: line('../etc')}]}),
    update({games: [{block: 'games', line: line('CUSA00001', {art: null})}]}),
    update({releases: {'CUSA00001/../x': []}}),
    update({releases: {CUSA00001: [{id: 'r1'}]}}),
    update({pages: {CUSA00001: {about: 'Text'}}}),
    update({removed: ['nope']}),
  ];
  for (const item of broken) assert.equal(valid(item), false, JSON.stringify(item).slice(0, 120));
});

test('applying replaces entries in whichever block, adds new ones and removes the gone', () => {
  const games = [{id: 'CUSA00001', title: 'Old'}, {id: 'CUSA00009', title: 'Gone'}, {id: 'CUSA00005', title: 'Kept'}];
  const twins = [{id: 'PPSA00002', title: 'Old twin'}];
  const files = applyUpdate(update(), games, twins);
  assert.deepEqual(games.map((game) => game.id), ['CUSA00005', 'CUSA00001']);
  assert.equal(games[1].title, 'Demo CUSA00001');
  assert.deepEqual(twins.map((game) => game.id), ['PPSA00002']);
  assert.equal(twins[0].work, 7);
  assert.equal(JSON.parse(files.get('data/releases/CUSA00001.json'))[0].id, 'r1');
  assert.equal(files.get('data/releases/CUSA00003.json'), null);
  assert.deepEqual(JSON.parse(files.get('data/pages/CUSA00001.json')).about, ['Text']);
});

// A file tools/catalog-update.py wrote, when one is given (CATALOG_UPDATE=path): the app takes it.
test('an update the tool wrote passes the app\'s checks', {skip: !process.env.CATALOG_UPDATE}, () => {
  assert.equal(valid(JSON.parse(readFileSync(process.env.CATALOG_UPDATE, 'utf8'))), true);
});
