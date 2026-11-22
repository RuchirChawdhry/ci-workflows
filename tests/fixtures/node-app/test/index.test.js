import assert from 'node:assert/strict';
import test from 'node:test';
import { add } from '../src/index.js';

test('addition', () => {
  assert.equal(add(2, 3), 5);
});
