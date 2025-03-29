import { execSync } from 'child_process';
import { mkdirSync } from 'fs';
import { join } from 'path';

// Create contracts/types directory if it doesn't exist
mkdirSync(join(__dirname, '../frontend/src/contracts/types'), { recursive: true });

// Generate TypeScript types from Solidity contract
execSync('npx hardhat typechain', { stdio: 'inherit' }); 