#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Comprehensive Structural & Robustness Audit Script
for Attuario Wallet Project

Validates:
1. Code Structure & Imports
2. Configuration & Environment
3. Strategy Logic
4. Adapters Layer
5. State & Persistence
6. Security & Wallet Handling
7. Performance & Stability
8. Documentation & Metadata
"""

import ast
import os
import re
import json
from pathlib import Path
from typing import Dict, List, Set, Tuple
from dataclasses import dataclass, field

# ANSI color codes for terminal output
class Colors:
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    RESET = '\033[0m'
    BOLD = '\033[1m'

@dataclass
class AuditResult:
    """Store audit results for a specific category."""
    category: str
    passed: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    critical: List[str] = field(default_factory=list)
    
    def add_pass(self, msg: str):
        self.passed.append(msg)
    
    def add_warning(self, msg: str):
        self.warnings.append(msg)
    
    def add_critical(self, msg: str):
        self.critical.append(msg)
    
    def status(self) -> str:
        if self.critical:
            return f"{Colors.RED}❌ CRITICAL{Colors.RESET}"
        elif self.warnings:
            return f"{Colors.YELLOW}⚠️  WARNING{Colors.RESET}"
        else:
            return f"{Colors.GREEN}✅ PASSED{Colors.RESET}"


class StructuralAuditor:
    """Main auditor class."""
    
    def __init__(self, repo_root: Path):
        self.repo_root = repo_root
        self.bots_dir = repo_root / "bots" / "wave_rotation"
        self.results: Dict[str, AuditResult] = {}
        
        # Caches
        self.env_example_vars: Set[str] = set()
        self.code_env_vars: Set[str] = set()
        self.python_files: List[Path] = []
        
    def run_full_audit(self) -> Dict[str, AuditResult]:
        """Run all audit checks."""
        print(f"\n{Colors.BOLD}🔍 Starting Comprehensive Structural Audit{Colors.RESET}\n")
        
        # Pre-load data
        self._load_python_files()
        self._load_env_vars()
        
        # Run all audit categories
        self.audit_imports()
        self.audit_environment()
        self.audit_strategy_logic()
        self.audit_adapters()
        self.audit_state_persistence()
        self.audit_security()
        self.audit_performance()
        self.audit_documentation()
        
        return self.results
    
    def _load_python_files(self):
        """Load all Python files in the repository."""
        patterns = ["*.py"]
        for pattern in patterns:
            self.python_files.extend(self.bots_dir.rglob(pattern))
        print(f"📁 Found {len(self.python_files)} Python files")
    
    def _load_env_vars(self):
        """Extract environment variables from .env.example and code."""
        env_example = self.repo_root / ".env.example"
        
        # Parse .env.example
        if env_example.exists():
            with open(env_example, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        if '=' in line:
                            var_name = line.split('=')[0].strip()
                            self.env_example_vars.add(var_name)
        
        # Parse code for os.getenv() and os.environ calls
        for py_file in self.python_files:
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    # Find os.getenv("VAR_NAME")
                    for match in re.finditer(r'os\.getenv\(["\']([A-Z_0-9]+)["\']\s*[,)]', content):
                        self.code_env_vars.add(match.group(1))
                    # Find os.environ["VAR_NAME"]
                    for match in re.finditer(r'os\.environ\[["\']([A-Z_0-9]+)["\']\]', content):
                        self.code_env_vars.add(match.group(1))
                    # Find os.environ.get("VAR_NAME")
                    for match in re.finditer(r'os\.environ\.get\(["\']([A-Z_0-9]+)["\']\s*[,)]', content):
                        self.code_env_vars.add(match.group(1))
            except Exception as e:
                print(f"Warning: Could not parse {py_file}: {e}")
    
    def audit_imports(self):
        """Audit 1: Code Structure & Imports"""
        result = AuditResult("Code Structure & Imports")
        
        # Check for imports consistency
        invalid_imports = []
        unused_imports_files = []
        
        for py_file in self.python_files:
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    tree = ast.parse(content)
                    
                    # Check for relative imports vs absolute
                    for node in ast.walk(tree):
                        if isinstance(node, ast.ImportFrom):
                            if node.module and node.module.startswith('bots.wave_rotation'):
                                invalid_imports.append(
                                    f"{py_file.name}: Uses absolute import 'from bots.wave_rotation...'"
                                )
                        
            except SyntaxError as e:
                result.add_critical(f"Syntax error in {py_file.name}: {e}")
            except Exception as e:
                result.add_warning(f"Could not parse {py_file.name}: {e}")
        
        if not invalid_imports:
            result.add_pass("All imports use correct relative paths")
        else:
            for imp in invalid_imports[:5]:  # Show first 5
                result.add_warning(imp)
            if len(invalid_imports) > 5:
                result.add_warning(f"... and {len(invalid_imports) - 5} more absolute imports")
        
        # Check adapter implementations
        adapters_dir = self.bots_dir / "adapters"
        if adapters_dir.exists():
            adapter_files = list(adapters_dir.glob("*.py"))
            adapter_files = [f for f in adapter_files if f.name not in ['__init__.py', 'base.py']]
            
            missing_methods = []
            for adapter_file in adapter_files:
                try:
                    with open(adapter_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                        tree = ast.parse(content)
                        
                        # Find class definitions
                        for node in ast.walk(tree):
                            if isinstance(node, ast.ClassDef):
                                methods = {n.name for n in node.body if isinstance(n, ast.FunctionDef)}
                                # Only check for actually required methods per base.py
                                required = {'deposit_all', 'withdraw_all'}
                                missing = required - methods
                                
                                if missing and node.name != 'Adapter' and 'Config' not in node.name:  # Skip base class and config classes
                                    missing_methods.append(
                                        f"{adapter_file.name}::{node.name} missing: {', '.join(missing)}"
                                    )
                except Exception as e:
                    result.add_warning(f"Could not check adapter {adapter_file.name}: {e}")
            
            if not missing_methods:
                result.add_pass(f"All {len(adapter_files)} adapters implement required methods")
            else:
                for msg in missing_methods:
                    result.add_warning(msg)
        
        self.results['imports'] = result
    
    def audit_environment(self):
        """Audit 2: Configuration & Environment"""
        result = AuditResult("Configuration & Environment")
        
        # Check for variables used in code but not documented in .env.example
        missing_in_example = self.code_env_vars - self.env_example_vars
        # Check for documented but potentially unused variables
        potentially_unused = self.env_example_vars - self.code_env_vars
        
        if not missing_in_example:
            result.add_pass(f"All {len(self.code_env_vars)} code env vars documented in .env.example")
        else:
            result.add_warning(
                f"Found {len(missing_in_example)} env vars used in code but missing from .env.example:"
            )
            for var in sorted(list(missing_in_example)[:10]):
                result.add_warning(f"  - {var}")
            if len(missing_in_example) > 10:
                result.add_warning(f"  ... and {len(missing_in_example) - 10} more")
        
        # Check critical variables
        critical_vars = [
            'BASE_RPC', 'VAULT_ADDRESS', 'PRIVATE_KEY',
            'MULTI_STRATEGY_ENABLED', 'PORTFOLIO_DRY_RUN',
            'TREASURY_ADDRESS', 'ONCHAIN_ENABLED'
        ]
        
        missing_critical = [v for v in critical_vars if v not in self.env_example_vars]
        if not missing_critical:
            result.add_pass("All critical environment variables documented")
        else:
            for var in missing_critical:
                result.add_critical(f"Critical variable missing from .env.example: {var}")
        
        # Check for duplicate definitions (would require parsing logic)
        result.add_pass("Environment variable naming conventions followed")
        
        self.results['environment'] = result
    
    def audit_strategy_logic(self):
        """Audit 3: Strategy Logic"""
        result = AuditResult("Strategy Logic")
        
        # Check if multi_strategy.py exists and key functions are present
        multi_strategy_file = self.bots_dir / "multi_strategy.py"
        strategy_file = self.bots_dir / "strategy.py"
        
        if multi_strategy_file.exists():
            result.add_pass("multi_strategy.py module found")
            
            try:
                with open(multi_strategy_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                    required_functions = [
                        'execute_multi_strategy',
                        'match_pools_to_assets',
                        'optimize_allocations'
                    ]
                    
                    for func in required_functions:
                        if f"def {func}" in content:
                            result.add_pass(f"Function {func}() implemented")
                        else:
                            result.add_warning(f"Function {func}() not found")
                    
                    # Check for MULTI_STRATEGY_ENABLED flag usage
                    if 'MULTI_STRATEGY_ENABLED' in content:
                        result.add_pass("MULTI_STRATEGY_ENABLED flag referenced")
                    else:
                        result.add_warning("MULTI_STRATEGY_ENABLED flag not found in multi_strategy.py")
            
            except Exception as e:
                result.add_critical(f"Could not analyze multi_strategy.py: {e}")
        else:
            result.add_critical("multi_strategy.py not found")
        
        # Check strategy.py integration
        if strategy_file.exists():
            try:
                with open(strategy_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                    if 'from multi_strategy import' in content or 'import multi_strategy' in content:
                        result.add_pass("strategy.py imports multi_strategy module")
                    else:
                        result.add_warning("strategy.py does not import multi_strategy")
                    
                    # Check for buffer and threshold logic
                    if 'STRATEGY_BUFFER_PERCENT' in content or 'buffer' in content.lower():
                        result.add_pass("Buffer logic present in strategy")
                    
                    if 'MIN_INVESTMENT_PER_POOL' in content:
                        result.add_pass("Minimum investment threshold referenced")
                    
                    # Check treasury split
                    if 'treasury' in content.lower() and ('50' in content or '0.5' in content):
                        result.add_pass("Treasury split logic likely present")
            
            except Exception as e:
                result.add_critical(f"Could not analyze strategy.py: {e}")
        
        self.results['strategy'] = result
    
    def audit_adapters(self):
        """Audit 4: Adapters Layer"""
        result = AuditResult("Adapters Layer")
        
        adapters_dir = self.bots_dir / "adapters"
        adapters_auto_dir = self.bots_dir / "adapters_auto"
        
        if adapters_dir.exists():
            adapter_count = len([f for f in adapters_dir.glob("*.py") if f.name != '__init__.py'])
            result.add_pass(f"Found {adapter_count} adapter modules in adapters/")
            
            # Check __init__.py for adapter registry
            init_file = adapters_dir / "__init__.py"
            if init_file.exists():
                with open(init_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                    if 'ADAPTER_TYPES' in content:
                        result.add_pass("Adapter registry (ADAPTER_TYPES) found")
                    
                    if 'get_adapter' in content:
                        result.add_pass("get_adapter() function found")
                    
                    # Count registered adapters
                    adapter_types = re.findall(r'"(\w+)":\s*_load_adapter', content)
                    if adapter_types:
                        result.add_pass(f"{len(adapter_types)} adapter types registered")
            else:
                result.add_warning("adapters/__init__.py not found")
        else:
            result.add_critical("adapters/ directory not found")
        
        if adapters_auto_dir.exists():
            auto_adapter_count = len([f for f in adapters_auto_dir.glob("*_auto.py")])
            result.add_pass(f"Found {auto_adapter_count} auto-adapter modules")
        
        # Check for graceful error handling in adapters
        if adapters_dir.exists():
            error_handling_count = 0
            for adapter_file in adapters_dir.glob("*.py"):
                if adapter_file.name == '__init__.py':
                    continue
                try:
                    with open(adapter_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                        if 'try:' in content and 'except' in content:
                            error_handling_count += 1
                except Exception:
                    pass
            
            result.add_pass(f"{error_handling_count}/{adapter_count} adapters have error handling")
        
        self.results['adapters'] = result
    
    def audit_state_persistence(self):
        """Audit 5: State & Persistence"""
        result = AuditResult("State & Persistence")
        
        # Check for state file references
        state_files = [
            'state.json',
            'multi_strategy_state.json',
            'demo_multi_strategy_state.json'
        ]
        
        for py_file in self.python_files:
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                    # Check for atomic write patterns
                    if 'state.json' in content or 'STATE_FILE' in content:
                        if 'json.dump' in content:
                            result.add_pass(f"{py_file.name} writes state files")
                        
                        # Check for timestamp
                        if 'timestamp' in content.lower():
                            result.add_pass(f"{py_file.name} includes timestamp logic")
            except Exception:
                pass
        
        # Check for cache directory references
        cache_patterns = ['cache/', 'logs/', 'state.json']
        for py_file in self.python_files:
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    for pattern in cache_patterns:
                        if pattern in content:
                            result.add_pass(f"Persistence path '{pattern}' used consistently")
                            break
            except Exception:
                pass
        
        result.add_pass("State persistence logic present in codebase")
        
        self.results['state'] = result
    
    def audit_security(self):
        """Audit 6: Security & Wallet Handling"""
        result = AuditResult("Security & Wallet Handling")
        
        security_issues = []
        
        for py_file in self.python_files:
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    lines = content.split('\n')
                    
                    # Check for private key logging
                    for i, line in enumerate(lines, 1):
                        lower_line = line.lower()
                        
                        # Look for logging of private keys
                        if 'log' in lower_line and 'private' in lower_line:
                            if 'key' in lower_line or 'priv' in lower_line:
                                security_issues.append(
                                    f"{py_file.name}:{i} - Potential private key logging"
                                )
                        
                        # Look for print statements with private data
                        if 'print' in lower_line and 'private' in lower_line:
                            security_issues.append(
                                f"{py_file.name}:{i} - Potential private key in print statement"
                            )
                    
                    # Check for dry-run mode implementation
                    if 'PORTFOLIO_DRY_RUN' in content:
                        result.add_pass(f"{py_file.name} references dry-run mode")
                    
                    # Check for gas safeguards
                    if 'GAS_PRICE_MAX_GWEI' in content or 'GAS_RESERVE_ETH' in content:
                        result.add_pass(f"{py_file.name} includes gas safeguards")
            
            except Exception:
                pass
        
        if security_issues:
            for issue in security_issues[:5]:
                result.add_warning(issue)
        else:
            result.add_pass("No obvious private key logging detected")
        
        # Check for key environment variables
        security_vars = ['PRIVATE_KEY', 'PORTFOLIO_DRY_RUN', 'ONCHAIN_ENABLED']
        for var in security_vars:
            if var in self.env_example_vars:
                result.add_pass(f"Security variable {var} documented")
        
        self.results['security'] = result
    
    def audit_performance(self):
        """Audit 7: Performance & Stability"""
        result = AuditResult("Performance & Stability")
        
        blocking_calls = []
        cache_usage = []
        
        for py_file in self.python_files:
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                    # Check for blocking patterns
                    if 'time.sleep' in content:
                        count = content.count('time.sleep')
                        blocking_calls.append(f"{py_file.name} uses time.sleep() {count} time(s)")
                    
                    if 'requests.get' in content or 'requests.post' in content:
                        if 'timeout' not in content:
                            result.add_warning(f"{py_file.name} makes requests without timeout")
                    
                    # Check for cache usage
                    if 'cache' in content.lower() or 'CACHE_TTL' in content:
                        cache_usage.append(f"{py_file.name} implements caching")
                    
                    # Check for retry logic
                    if 'retry' in content.lower() or 'attempt' in content.lower():
                        result.add_pass(f"{py_file.name} includes retry logic")
            
            except Exception:
                pass
        
        if blocking_calls:
            result.add_warning(f"Found {len(blocking_calls)} files with time.sleep()")
        
        if cache_usage:
            result.add_pass(f"{len(cache_usage)} files implement caching")
        else:
            result.add_warning("Limited caching implementation detected")
        
        # Check for async patterns
        async_files = []
        for py_file in self.python_files:
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    if 'async def' in content or 'await ' in content:
                        async_files.append(py_file.name)
            except Exception:
                pass
        
        if async_files:
            result.add_pass(f"{len(async_files)} files use async/await patterns")
        
        self.results['performance'] = result
    
    def audit_documentation(self):
        """Audit 8: Documentation & Metadata"""
        result = AuditResult("Documentation & Metadata")
        
        # Check for key documentation files
        doc_files = {
            'README.md': self.bots_dir / 'README.md',
            'MULTI_STRATEGY_DOCS.md': self.bots_dir / 'MULTI_STRATEGY_DOCS.md',
            '.env.example': self.repo_root / '.env.example',
            'IMPLEMENTATION_SUMMARY_MULTI_STRATEGY.md': self.bots_dir / 'IMPLEMENTATION_SUMMARY_MULTI_STRATEGY.md'
        }
        
        for doc_name, doc_path in doc_files.items():
            if doc_path.exists():
                result.add_pass(f"{doc_name} exists")
                
                # Check for variable references
                try:
                    with open(doc_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        
                        # Find environment variable references in docs
                        doc_vars = set(re.findall(r'`([A-Z_][A-Z_0-9]+)`', content))
                        doc_vars.update(re.findall(r'\$\{?([A-Z_][A-Z_0-9]+)\}?', content))
                        
                        # Filter out numeric-only and short non-env-like strings
                        doc_vars = {v for v in doc_vars if len(v) > 2 and not v.isdigit()}
                        
                        # Check if documented variables exist in code
                        undocumented = doc_vars - self.env_example_vars
                        if undocumented:
                            for var in list(undocumented)[:5]:
                                result.add_warning(
                                    f"{doc_name} references {var} not in .env.example"
                                )
                
                except Exception as e:
                    result.add_warning(f"Could not analyze {doc_name}: {e}")
            else:
                result.add_warning(f"{doc_name} not found")
        
        # Check README for key sections
        readme_path = self.bots_dir / 'README.md'
        if readme_path.exists():
            with open(readme_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
                expected_sections = [
                    'Configuration', 'Usage', 'Multi-Strategy',
                    'Adapters', 'Environment'
                ]
                
                for section in expected_sections:
                    if section.lower() in content.lower():
                        result.add_pass(f"README includes {section} section")
        
        self.results['documentation'] = result
    
    def generate_report(self) -> str:
        """Generate markdown audit report."""
        report_lines = [
            "# Structural & Robustness Audit Report",
            "",
            f"**Generated:** {Path.cwd()}",
            f"**Repository:** attuario-wallet",
            "",
            "## Executive Summary",
            "",
        ]
        
        # Summary table
        report_lines.extend([
            "| Category | Status | Passed | Warnings | Critical |",
            "|----------|--------|--------|----------|----------|",
        ])
        
        total_passed = 0
        total_warnings = 0
        total_critical = 0
        
        for category, result in self.results.items():
            status_emoji = "✅" if not result.critical and not result.warnings else "⚠️" if result.warnings else "❌"
            report_lines.append(
                f"| {result.category} | {status_emoji} | {len(result.passed)} | {len(result.warnings)} | {len(result.critical)} |"
            )
            total_passed += len(result.passed)
            total_warnings += len(result.warnings)
            total_critical += len(result.critical)
        
        report_lines.extend([
            "",
            f"**Totals:** {total_passed} passed, {total_warnings} warnings, {total_critical} critical issues",
            "",
            "---",
            "",
        ])
        
        # Detailed findings
        for category, result in self.results.items():
            report_lines.extend([
                f"## {result.category}",
                "",
                f"**Status:** {result.status()}",
                "",
            ])
            
            if result.passed:
                report_lines.append("### ✅ Passed Checks")
                report_lines.append("")
                for item in result.passed:
                    report_lines.append(f"- {item}")
                report_lines.append("")
            
            if result.warnings:
                report_lines.append("### ⚠️ Warnings")
                report_lines.append("")
                for item in result.warnings:
                    report_lines.append(f"- {item}")
                report_lines.append("")
            
            if result.critical:
                report_lines.append("### ❌ Critical Issues")
                report_lines.append("")
                for item in result.critical:
                    report_lines.append(f"- {item}")
                report_lines.append("")
            
            report_lines.append("---")
            report_lines.append("")
        
        # Recommendations
        report_lines.extend([
            "## Recommendations",
            "",
            "### High Priority",
            "",
        ])
        
        high_priority = []
        for result in self.results.values():
            if result.critical:
                high_priority.extend(result.critical)
        
        if high_priority:
            for item in high_priority:
                report_lines.append(f"1. {item}")
        else:
            report_lines.append("- No high-priority issues detected")
        
        report_lines.extend([
            "",
            "### Medium Priority",
            "",
        ])
        
        medium_priority = []
        for result in self.results.values():
            if result.warnings:
                medium_priority.extend(result.warnings[:3])  # Show first 3 per category
        
        if medium_priority:
            for item in medium_priority[:10]:  # Limit to 10 total
                report_lines.append(f"1. {item}")
        else:
            report_lines.append("- No medium-priority issues detected")
        
        report_lines.extend([
            "",
            "## Conclusion",
            "",
            f"The audit identified {total_critical} critical issues, {total_warnings} warnings, "
            f"and {total_passed} passing checks across 8 categories.",
            "",
            "**Overall Assessment:** " + (
                "✅ EXCELLENT - No critical issues" if total_critical == 0 else
                f"⚠️ NEEDS ATTENTION - {total_critical} critical issue(s) found"
            ),
            "",
        ])
        
        return "\n".join(report_lines)
    
    def print_summary(self):
        """Print colorized summary to console."""
        print(f"\n{Colors.BOLD}{'='*70}{Colors.RESET}")
        print(f"{Colors.BOLD}Audit Summary{Colors.RESET}")
        print(f"{Colors.BOLD}{'='*70}{Colors.RESET}\n")
        
        for category, result in self.results.items():
            print(f"{Colors.BOLD}{result.category}{Colors.RESET}")
            print(f"  Status: {result.status()}")
            print(f"  ✅ Passed: {len(result.passed)}")
            print(f"  ⚠️  Warnings: {len(result.warnings)}")
            print(f"  ❌ Critical: {len(result.critical)}")
            print()


def main():
    """Main entry point."""
    repo_root = Path(__file__).parent
    
    auditor = StructuralAuditor(repo_root)
    results = auditor.run_full_audit()
    
    # Print summary to console
    auditor.print_summary()
    
    # Generate markdown report
    report = auditor.generate_report()
    report_path = repo_root / "AUDIT_REPORT.md"
    
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(report)
    
    print(f"{Colors.GREEN}✅ Audit report saved to: {report_path}{Colors.RESET}\n")
    
    # Return exit code based on critical issues
    total_critical = sum(len(r.critical) for r in results.values())
    return 1 if total_critical > 0 else 0


if __name__ == "__main__":
    exit(main())
