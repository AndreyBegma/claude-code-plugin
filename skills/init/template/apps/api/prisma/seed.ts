import 'dotenv/config';
import { PrismaPg } from '@prisma/adapter-pg';
import { PrismaClient } from '@prisma/client';

const prisma = new PrismaClient({
  adapter: new PrismaPg({ connectionString: process.env.DATABASE_URL }),
});

async function main() {
  await prisma.user.upsert({
    where: { email: 'admin@__SCOPE__.dev' },
    update: {},
    create: {
      email: 'admin@__SCOPE__.dev',
      name: 'Admin',
    },
  });

  console.log('Seed complete');
}

main()
  .catch((error) => {
    console.error(error);
    process.exitCode = 1;
  })
  .finally(() => prisma.$disconnect());
