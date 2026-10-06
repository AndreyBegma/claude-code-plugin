import { HealthController } from './health.controller';

describe('HealthController', () => {
  it('reports ok', () => {
    const result = new HealthController().check();

    expect(result.status).toBe('ok');
    expect(Number.isNaN(Date.parse(result.timestamp))).toBe(false);
  });
});
