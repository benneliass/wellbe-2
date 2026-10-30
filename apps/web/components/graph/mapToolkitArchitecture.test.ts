import { readdirSync, readFileSync } from 'node:fs';
import { dirname, join, resolve } from 'node:path';
import { describe, expect, it } from 'vitest';

const root = resolve(process.cwd(), '../../packages/ui/src/map');
function sources(directory: string): string[] {
  return readdirSync(directory, { withFileTypes: true }).flatMap((entry) => {
    const path = join(directory, entry.name);
    return entry.isDirectory() ? sources(path) : /\.(ts|tsx)$/.test(entry.name) ? [path] : [];
  });
}

describe('map toolkit dependency boundary', () => {
  it('stays portable without application models, routes, services or persistence', () => {
    for (const path of sources(root)) {
      const source = readFileSync(path, 'utf8');
      const dependencies = [...source.matchAll(/(?:from\s*|import\s*)['"]([^'"]+)['"]/g)].map((match) => match[1]!);
      for (const dependency of dependencies) {
        if (dependency.startsWith('.')) expect(resolve(dirname(path), dependency).startsWith(`${root}/`), path).toBe(true);
        else expect(dependency, path).toBe('react');
      }
      expect(source, path).not.toMatch(/\b(?:localStorage|sessionStorage|fetch)\s*[.(]/);
    }
  });

  it('keeps the math and routing entry point usable without a React host', () => {
    for (const path of sources(join(root, 'core'))) {
      expect(readFileSync(path, 'utf8'), path).not.toMatch(/from\s*['"]react|from\s*['"]\.\.\//);
    }
  });
});
