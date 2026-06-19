# How to Get Jenkins Evidence for OSS Compliance

## Current Problem

The scanner cannot find Jenkins jobs for `dsp-catalog-svc` because:
1. **Job naming mismatch**: Jenkins jobs may use different naming conventions
2. **Simple substring matching**: Current logic only matches exact repository name
3. **No fallback mechanisms**: If no jobs found, no evidence collected

## Solutions (Ranked by Effort)

---

## Option 1: Improve Jenkins Job Discovery (RECOMMENDED)

**Effort**: Low | **Impact**: High | **Timeline**: 1-2 hours

### What to Add:

#### A. Fuzzy Job Name Matching

Current logic:
```python
if repo_name.lower() in job_name.lower():  # Only exact substring match
```

Enhanced logic:
```python
def _matches_repository(self, job_name: str, repo_name: str) -> bool:
    """Check if Jenkins job matches repository using multiple strategies"""
    job_lower = job_name.lower()
    repo_lower = repo_name.lower()
    
    # Strategy 1: Exact substring match
    if repo_lower in job_lower:
        return True
    
    # Strategy 2: Match with underscores/hyphens normalized
    repo_normalized = repo_lower.replace('-', '').replace('_', '')
    job_normalized = job_lower.replace('-', '').replace('_', '')
    if repo_normalized in job_normalized:
        return True
    
    # Strategy 3: Match individual words (for multi-word repos)
    repo_words = set(repo_lower.replace('-', ' ').replace('_', ' ').split())
    job_words = set(job_lower.replace('-', ' ').replace('_', ' ').split())
    
    # If 2+ words match, consider it a match
    if len(repo_words) >= 2 and len(repo_words.intersection(job_words)) >= 2:
        return True
    
    # Strategy 4: Acronym matching (e.g., "dsp-catalog-svc" -> "dcs")
    repo_acronym = ''.join([word[0] for word in repo_words if word])
    if len(repo_acronym) >= 3 and repo_acronym in job_lower:
        return True
    
    return False
```

**Example Matches for `dsp-catalog-svc`:**
- ✅ `DSP-Catalog-Service`
- ✅ `dsp_catalog_svc`
- ✅ `catalog-svc-multibranch`
- ✅ `DSP-Catalog`
- ✅ `dcs-pipeline` (acronym)

#### B. GitHub URL Matching

Many Jenkins jobs include the GitHub URL in their configuration:

```python
def _check_job_github_url(self, job_config_xml: str, repo_name: str, github_url: str) -> bool:
    """Check if Jenkins job config references the GitHub repository"""
    # Look for GitHub URL in job config
    repo_url_patterns = [
        f"{github_url}/{repo_name}",
        f"{github_url}/{repo_name}.git",
        repo_name  # Just the repo name
    ]
    
    for pattern in repo_url_patterns:
        if pattern in job_config_xml:
            return True
    
    return False
```

#### C. Manual Job Mapping Configuration

Add a configuration file to manually map repositories to Jenkins jobs:

**config/jenkins_job_mappings.yaml:**
```yaml
jenkins_job_mappings:
  dsp-catalog-svc:
    - "DSP-Catalog-Service"
    - "catalog-service-multibranch"
  fusion-stage:
    - "fusion-stage"
    - "Stage-UI-System-Test-Services"
```

---

## Option 2: Add Alternative Evidence Sources

**Effort**: Medium | **Impact**: High | **Timeline**: 1-2 days

### A. Dockerfile Build Args Analysis

Many projects set proxy configuration in Dockerfile:

```python
def _extract_dockerfile_build_args(self, dockerfile_content: str) -> Dict:
    """Extract build-time environment variables from Dockerfile"""
    configs = {}
    
    # Look for ENV statements
    env_pattern = re.compile(r'ENV\s+(\w+)=(.+)', re.IGNORECASE)
    for match in env_pattern.finditer(dockerfile_content):
        var_name = match.group(1)
        var_value = match.group(2).strip()
        
        # Check for proxy configurations
        if var_name in ['GOPROXY', 'GOSUMDB', 'PIP_INDEX_URL', 'NPM_CONFIG_REGISTRY']:
            configs[var_name] = var_value
    
    return configs
```

### B. Makefile Target Analysis

Extract proxy configuration from Makefile targets:

```python
def _extract_makefile_configs(self, makefile_content: str) -> Dict:
    """Extract proxy configurations from Makefile"""
    configs = {}
    
    # Look for export statements
    export_pattern = re.compile(r'export\s+(\w+)\s*[:=]\s*(.+)', re.IGNORECASE)
    for match in export_pattern.finditer(makefile_content):
        var_name = match.group(1)
        var_value = match.group(2).strip()
        
        if var_name in ['GOPROXY', 'GOSUMDB', 'PIP_INDEX_URL']:
            configs[var_name] = var_value
    
    return configs
```

### C. CI/CD Configuration Files

Check for GitHub Actions, GitLab CI, or other CI configs:

```python
def _check_github_actions(self, repo_dir: Path) -> Dict:
    """Extract proxy configs from GitHub Actions workflows"""
    workflows_dir = repo_dir / '.github' / 'workflows'
    configs = {}
    
    if workflows_dir.exists():
        for workflow_file in workflows_dir.glob('*.yml'):
            with open(workflow_file) as f:
                workflow = yaml.safe_load(f)
                
                # Check for env variables in workflow
                if 'env' in workflow:
                    for key, value in workflow['env'].items():
                        if key in ['GOPROXY', 'PIP_INDEX_URL', 'NPM_CONFIG_REGISTRY']:
                            configs[key] = value
    
    return configs
```

---

## Option 3: Jenkins Plugin Integration

**Effort**: High | **Impact**: Very High | **Timeline**: 1 week

### Install Jenkins Plugin to Expose Build Metadata

Create a Jenkins plugin that:
1. Captures environment variables from every build
2. Stores them in a queryable format
3. Exposes an API endpoint for the scanner

**Plugin Features:**
- Capture `GOPROXY`, `PIP_INDEX_URL`, `NPM_CONFIG_REGISTRY` from builds
- Store last 10 builds' environment variables
- API endpoint: `/job/{jobName}/buildEnv/api/json`

**Scanner Integration:**
```python
def _get_jenkins_build_env(self, job_url: str, auth) -> Dict:
    """Get build environment variables from Jenkins plugin"""
    env_url = f"{job_url}buildEnv/api/json"
    response = self.session.get(env_url, auth=auth)
    
    if response.status_code == 200:
        return response.json()
    
    return {}
```

---

## Option 4: Repository Metadata File

**Effort**: Low | **Impact**: Medium | **Timeline**: 30 minutes

### Add Compliance Metadata to Repository

Create a `.compliance.yaml` file in each repository:

```yaml
# .compliance.yaml
oss_compliance:
  jenkins_jobs:
    - "DSP-Catalog-Service"
    - "catalog-service-multibranch"
  
  runtime_config:
    go:
      GOPROXY: "https://hopjpd.artifactory.cec.lab.emc.com/artifactory/api/go/isgedge-go-virtual"
      GOSUMDB: "off"
    
    python:
      PIP_INDEX_URL: "https://hopjpd.artifactory.cec.lab.emc.com/artifactory/api/pypi/isgedge-pypi-virtual/simple"
    
    npm:
      NPM_CONFIG_REGISTRY: "https://hopjpd.artifactory.cec.lab.emc.com/artifactory/api/npm/isgedge-npm-virtual/"
```

**Scanner reads this file and:**
1. Uses specified Jenkins jobs for evidence
2. Validates runtime config matches approved values
3. Marks components as compliant if config matches

---

## Option 5: Artifactory Download Logs

**Effort**: High | **Impact**: Very High | **Timeline**: 1-2 weeks

### Query Artifactory for Download Evidence

Instead of relying on Jenkins, query Artifactory directly:

```python
def _query_artifactory_downloads(self, component_name: str, artifactory_url: str) -> bool:
    """Check if component was downloaded from Artifactory"""
    # Query Artifactory API for download logs
    api_url = f"{artifactory_url}/api/search/artifact"
    params = {
        'name': component_name,
        'repos': 'isgedge-go-virtual,isgedge-pypi-virtual,isgedge-npm-virtual'
    }
    
    response = requests.get(api_url, params=params, auth=auth)
    
    if response.status_code == 200:
        results = response.json().get('results', [])
        return len(results) > 0
    
    return False
```

**Pros:**
- Direct evidence of Artifactory usage
- No dependency on Jenkins
- Works for all package managers

**Cons:**
- Requires Artifactory API access
- May have performance implications
- Doesn't prove the component was downloaded by THIS repository

---

## Recommended Implementation Plan

### Phase 1: Quick Wins (1-2 days)
1. ✅ **Improve job name matching** (Option 1A)
2. ✅ **Add GitHub URL matching** (Option 1B)
3. ✅ **Add manual job mapping config** (Option 1C)
4. ✅ **Extract Dockerfile ENV vars** (Option 2A)
5. ✅ **Extract Makefile exports** (Option 2B)

### Phase 2: Enhanced Detection (1 week)
6. ✅ **Check GitHub Actions workflows** (Option 2C)
7. ✅ **Add .compliance.yaml support** (Option 4)

### Phase 3: Advanced Integration (2-4 weeks)
8. ⏳ **Jenkins plugin development** (Option 3)
9. ⏳ **Artifactory API integration** (Option 5)

---

## Immediate Action for dsp-catalog-svc

### Manual Workaround (Today):

1. **Find the actual Jenkins job name:**
   ```bash
   # Search Jenkins for any jobs related to catalog or dsp
   curl -u jpurcell:$TOKEN https://osj-isg-03-prd.cec.delllabs.net/api/json?tree=jobs[name] | grep -i catalog
   ```

2. **Add manual mapping:**
   ```yaml
   # config/jenkins_job_mappings.yaml
   jenkins_job_mappings:
     dsp-catalog-svc:
       - "actual-jenkins-job-name"
   ```

3. **Re-scan** to get evidence

### Long-term Solution:

Implement **Phase 1** improvements to automatically discover jobs with fuzzy matching.

---

## Questions to Answer

1. **Does dsp-catalog-svc actually have Jenkins jobs?**
   - If yes: What are they named?
   - If no: How is it being built? (GitHub Actions? Local builds?)

2. **What CI/CD system is used?**
   - Jenkins
   - GitHub Actions
   - GitLab CI
   - Manual builds

3. **Where is proxy configuration set?**
   - Jenkins job environment variables
   - Dockerfile
   - Makefile
   - Shell scripts
   - CI/CD config files

Once we know these answers, we can implement the most appropriate solution.
