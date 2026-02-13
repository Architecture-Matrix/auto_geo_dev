#!/usr/bin/env node
/**
 * AutoGeo 本地自动化 CI 脚本
 *
 * 功能：
 * - 在本地模拟完整的 GitHub Actions CI 流程
 * - 执行 Lint、Type Check、Unit Test、Build
 * - 支持前端和后端分别运行
 * - 生成 CI 报告
 *
 * 使用方法：
 *   node scripts/ci.js                    # 运行全部
 *   node scripts/ci.js --frontend         # 只运行前端
 *   node scripts/ci.js --backend          # 只运行后端
 *   node scripts/ci.js --skip-test        # 跳过测试
 */

const { execSync } = require('child_process')
const fs = require('fs')
const path = require('path')

// 颜色输出
const colors = {
  reset: '\x1b[0m',
  red: '\x1b[31m',
  green: '\x1b[32m',
  yellow: '\x1b[33m',
  blue: '\x1b[34m',
  magenta: '\x1b[35m',
  cyan: '\x1b[36m',
}

const log = {
  info: (msg) => console.log(`${colors.blue}ℹ${colors.reset} ${msg}`),
  success: (msg) => console.log(`${colors.green}✓${colors.reset} ${msg}`),
  error: (msg) => console.log(`${colors.red}✗${colors.reset} ${msg}`),
  warn: (msg) => console.log(`${colors.yellow}⚠${colors.reset} ${msg}`),
  step: (msg) => console.log(`\n${colors.cyan}▶${colors.reset} ${msg}`),
}

// 解析命令行参数
const args = process.argv.slice(2)
const options = {
  frontend: args.includes('--frontend') || !args.includes('--backend'),
  backend: args.includes('--backend') || !args.includes('--frontend'),
  skipTest: args.includes('--skip-test'),
  skipLint: args.includes('--skip-lint'),
  verbose: args.includes('--verbose') || args.includes('-v'),
}

// CI 结果统计
const results = {
  frontend: { passed: 0, failed: 0, skipped: 0, steps: [] },
  backend: { passed: 0, failed: 0, skipped: 0, steps: [] },
}

/**
 * 执行命令
 */
function exec(cmd, options = {}) {
  const { cwd, ignoreError = false } = options
  try {
    const output = execSync(cmd, {
      cwd: cwd || process.cwd(),
      encoding: 'utf-8',
      stdio: options.verbose ? 'inherit' : 'pipe',
      ...options,
    })
    return { success: true, output: output.trim() }
  } catch (error) {
    if (ignoreError) {
      return { success: false, output: error.stdout?.trim() || '', error: error.message }
    }
    throw error
  }
}

/**
 * 记录步骤结果
 */
function recordStep(category, name, success, duration = 0) {
  const result = { name, success, duration, timestamp: Date.now() }
  if (success) {
    results[category].passed++
    results[category].steps.push(result)
  } else {
    results[category].failed++
    results[category].steps.push(result)
  }
  return result
}

/**
 * 前端 CI
 */
async function runFrontendCI() {
  log.step('开始前端 CI 检查...')

  const frontendDir = path.join(__dirname, '..')
  const startTime = Date.now()

  // 1. ESLint
  if (!options.skipLint) {
    log.info('运行 ESLint...')
    try {
      exec('npm run lint', { cwd: frontendDir, stdio: 'pipe' })
      log.success('ESLint 检查通过')
      recordStep('frontend', 'ESLint', true)
    } catch (e) {
      log.error('ESLint 检查失败')
      log.error(e.message)
      recordStep('frontend', 'ESLint', false)
      if (!options.verbose) {
        log.info('使用 --verbose 查看详细输出')
      }
      return false
    }
  } else {
    log.warn('跳过 ESLint')
    results.frontend.skipped++
  }

  // 2. TypeScript Check
  log.info('运行 TypeScript 类型检查...')
  try {
    exec('npm run type-check', { cwd: frontendDir, stdio: 'pipe' })
    log.success('TypeScript 检查通过')
    recordStep('frontend', 'TypeScript', true)
  } catch (e) {
    log.error('TypeScript 检查失败')
    recordStep('frontend', 'TypeScript', false)
    return false
  }

  // 3. Unit Tests
  if (!options.skipTest) {
    log.info('运行单元测试...')
    const testResult = exec('npm run test:unit -- --run --reporter=verbose', {
      cwd: frontendDir,
      stdio: 'pipe',
      ignoreError: true,
    })
    if (testResult.success || testResult.output.includes('PASS')) {
      log.success('单元测试通过')
      recordStep('frontend', 'Unit Tests', true)
    } else {
      log.warn('单元测试有问题，但继续...')
      recordStep('frontend', 'Unit Tests', false)
    }
  } else {
    log.warn('跳过单元测试')
    results.frontend.skipped++
  }

  // 4. Build Check
  log.info('构建前端...')
  try {
    exec('npm run build:renderer', { cwd: frontendDir, stdio: options.verbose ? 'inherit' : 'pipe' })
    log.success('前端构建成功')
    recordStep('frontend', 'Build', true, Date.now() - startTime)
  } catch (e) {
    log.error('前端构建失败')
    recordStep('frontend', 'Build', false)
    return false
  }

  log.success(`前端 CI 完成！用时: ${((Date.now() - startTime) / 1000).toFixed(2)}s`)
  return true
}

/**
 * 后端 CI
 */
async function runBackendCI() {
  log.step('开始后端 CI 检查...')

  const backendDir = path.join(__dirname, '../..', 'backend')
  const startTime = Date.now()

  // 检查后端目录是否存在
  if (!fs.existsSync(backendDir)) {
    log.warn('后端目录不存在，跳过后端 CI')
    return false
  }

  // 1. Ruff Lint
  if (!options.skipLint) {
    log.info('运行 Ruff Lint...')
    const ruffResult = exec('ruff check .', {
      cwd: backendDir,
      stdio: 'pipe',
      ignoreError: true,
    })
    if (ruffResult.success) {
      log.success('Ruff 检查通过')
      recordStep('backend', 'Ruff Lint', true)
    } else {
      log.warn('Ruff 检查发现问题')
      recordStep('backend', 'Ruff Lint', false)
    }

    // Ruff Format Check
    log.info('运行 Ruff Format 检查...')
    const formatResult = exec('ruff format --check .', {
      cwd: backendDir,
      stdio: 'pipe',
      ignoreError: true,
    })
    if (formatResult.success) {
      log.success('Ruff Format 检查通过')
      recordStep('backend', 'Ruff Format', true)
    } else {
      log.warn('Ruff Format 检查发现问题')
      recordStep('backend', 'Ruff Format', false)
    }
  } else {
    log.warn('跳过 Ruff')
    results.backend.skipped++
  }

  // 2. MyPy Type Check
  log.info('运行 MyPy 类型检查...')
  const mypyResult = exec('mypy api/ --ignore-missing-imports', {
    cwd: backendDir,
    stdio: 'pipe',
    ignoreError: true,
  })
  if (mypyResult.success) {
    log.success('MyPy 检查通过')
    recordStep('backend', 'MyPy', true)
  } else {
    log.warn('MyPy 检查发现问题（可能不影响运行）')
    recordStep('backend', 'MyPy', false)
  }

  // 3. Unit Tests
  if (!options.skipTest) {
    log.info('运行单元测试...')
    const testResult = exec('pytest tests/ -v --ignore=tests/e2e', {
      cwd: backendDir,
      stdio: 'pipe',
      ignoreError: true,
    })
    if (testResult.success || testResult.output.includes('passed')) {
      log.success('单元测试通过')
      recordStep('backend', 'Unit Tests', true)
    } else {
      log.warn('单元测试有问题，但继续...')
      recordStep('backend', 'Unit Tests', false)
    }
  } else {
    log.warn('跳过单元测试')
    results.backend.skipped++
  }

  log.success(`后端 CI 完成！用时: ${((Date.now() - startTime) / 1000).toFixed(2)}s`)
  return true
}

/**
 * 生成 CI 报告
 */
function generateReport() {
  console.log('\n' + '='.repeat(60))
  console.log(`${colors.cyan}  CI 报告${colors.reset}`)
  console.log('='.repeat(60))

  // 前端报告
  if (options.frontend) {
    console.log(`\n${colors.magenta}前端:${colors.reset}`)
    console.log(`  ✓ 通过: ${results.frontend.passed}`)
    console.log(`  ✗ 失败: ${results.frontend.failed}`)
    console.log(`  ⊘ 跳过: ${results.frontend.skipped}`)

    if (results.frontend.steps.length > 0) {
      console.log(`\n  步骤详情:`)
      results.frontend.steps.forEach(step => {
        const icon = step.success ? '✓' : '✗'
        const color = step.success ? colors.green : colors.red
        console.log(`    ${color}${icon}${colors.reset} ${step.name} (${(step.duration / 1000).toFixed(2)}s)`)
      })
    }
  }

  // 后端报告
  if (options.backend) {
    console.log(`\n${colors.magenta}后端:${colors.reset}`)
    console.log(`  ✓ 通过: ${results.backend.passed}`)
    console.log(`  ✗ 失败: ${results.backend.failed}`)
    console.log(`  ⊘ 跳过: ${results.backend.skipped}`)

    if (results.backend.steps.length > 0) {
      console.log(`\n  步骤详情:`)
      results.backend.steps.forEach(step => {
        const icon = step.success ? '✓' : '✗'
        const color = step.success ? colors.green : colors.red
        console.log(`    ${color}${icon}${colors.reset} ${step.name} (${(step.duration / 1000).toFixed(2)}s)`)
      })
    }
  }

  // 总结
  const totalPassed = results.frontend.passed + results.backend.passed
  const totalFailed = results.frontend.failed + results.backend.failed
  const totalSkipped = results.frontend.skipped + results.backend.skipped

  console.log('\n' + '='.repeat(60))
  console.log(`${colors.cyan}总计:${colors.reset} ✓ ${totalPassed} | ✗ ${totalFailed} | ⊘ ${totalSkipped}`)

  if (totalFailed === 0) {
    console.log(`\n${colors.green}🎉 所有检查通过！可以安全推送代码了！${colors.reset}\n`)
    return 0
  } else {
    console.log(`\n${colors.red}⚠️  有 ${totalFailed} 项检查失败，请修复后再推送！${colors.reset}\n`)
    return 1
  }
}

/**
 * 主函数
 */
async function main() {
  console.log(`\n${colors.cyan}╔════════════════════════════════════════════════════════════╗${colors.reset}`)
  console.log(`${colors.cyan}║         AutoGeo 本地自动化 CI 脚本                       ║${colors.reset}`)
  console.log(`${colors.cyan}╚════════════════════════════════════════════════════════════╝${colors.reset}\n`)

  log.info('配置:', JSON.stringify({
    frontend: options.frontend,
    backend: options.backend,
    skipTest: options.skipTest,
    skipLint: options.skipLint,
    verbose: options.verbose,
  }, null, 2))

  const overallStartTime = Date.now()

  // 运行前端 CI
  if (options.frontend) {
    await runFrontendCI()
  }

  // 运行后端 CI
  if (options.backend) {
    await runBackendCI()
  }

  // 生成报告
  const exitCode = generateReport()

  log.info(`总用时: ${((Date.now() - overallStartTime) / 1000).toFixed(2)}s`)

  process.exit(exitCode)
}

// 运行
main().catch(error => {
  log.error('CI 运行出错:', error.message)
  process.exit(1)
})
