# Repository Classification System Specification
## OSS Compliance Web Application

**Document Version:** 1.0  
**Application Version:** 0.5.0  
**Last Updated:** 2026-06-23  
**Status:** Draft  

---

## 1. Overview

### 1.1 Purpose
This specification defines the repository classification system for the OSS Compliance Web Application, addressing the accurate handling of different repository types including minimal repositories, runtime-only repositories, and monorepos.

### 1.2 Background
Analysis of the fusion-stage-backend repository revealed that it returns 0 OSS components and 0% compliance, which is technically accurate but potentially misleading. The repository contains only a README.md file with no OSS dependency files, yet Jenkins logs show runtime evidence of Python package installation from AWS CodeArtifact. This discrepancy highlights the need for a repository classification system to provide accurate compliance assessment across different repository structures.

### 1.3 Scope
This specification covers:
- Repository classification categories and detection algorithms
- Minimal repository handling and user experience
- Runtime evidence vs. static file analysis integration
- Monorepo support considerations
- Compliance reporting enhancements

---

## 2. Repository Classification Categories

### 2.1 Standard Repository

**Definition**: Repository containing OSS dependency files and source code.

**Characteristics**:
- Contains dependency files: go.mod, requirements.txt, package.json, pom.xml, setup.py, pyproject.toml
- Contains source code files
- May contain configuration files (Dockerfile, Makefile, Jenkinsfile)
- Can be scanned for component enumeration

**Compliance Assessment**:
- Full component enumeration and compliance analysis
- Compliance percentage: 0-100% based on component compliance
- Normal scanning and reporting workflow

**Examples**: fusion-stage, fusion-plugins-service

### 2.2 Minimal Repository

**Definition**: Repository with minimal content, typically containing only documentation or placeholder files.

**Characteristics**:
- No OSS dependency files
- Minimal file structure (typically only README.md)
- No source code or configuration files
- May be a placeholder, sub-module, or external dependency pointer

**Compliance Assessment**:
- Static file analysis returns 0 components
- Special status: "No OSS components detected" with contextual information
- Runtime evidence analysis if available from Jenkins
- Compliance percentage: Not applicable (N/A) or 0% with explanation

**Examples**: fusion-stage-backend

### 2.3 Runtime-Only Repository

**Definition**: Repository with no static OSS files but with runtime evidence from build systems.

**Characteristics**:
- No static OSS dependency files
- Runtime evidence available from Jenkins logs
- Dependencies may be injected during build process
- Often build infrastructure or configuration repositories

**Compliance Assessment**:
- Compliance based on runtime configuration evidence
- Requires Jenkins integration for assessment
- Displays runtime configuration details
- Compliance percentage based on runtime evidence analysis

**Examples**: Build infrastructure repositories, configuration repositories

### 2.4 Monorepo

**Definition**: Repository containing multiple projects with shared dependencies.

**Characteristics**:
- Multiple projects in single repository
- Shared dependencies across projects
- Hierarchical project structure
- Complex dependency relationships

**Compliance Assessment**:
- Requires hierarchical analysis and dependency mapping
- Project-level and repository-level compliance reporting
- Shared dependency tracking
- Selective scanning capabilities

**Status**: Future enhancement (planned support)

---

## 3. Classification Algorithm

### 3.1 Detection Logic

```python
def classify_repository(repo_analysis):
    """
    Classify repository based on content and structure analysis.
    
    Args:
        repo_analysis: Dictionary containing repository analysis results
        
    Returns:
        str: Repository classification (STANDARD, MINIMAL, RUNTIME_ONLY, MONOREPO, UNKNOWN)
    """
    if has_dependency_files(repo_analysis):
        if is_monorepo_structure(repo_analysis):
            return "MONOREPO"
        else:
            return "STANDARD"
    elif has_runtime_evidence(repo_analysis):
        return "RUNTIME_ONLY"
    elif is_minimal_content(repo_analysis):
        return "MINIMAL"
    else:
        return "UNKNOWN"
```

### 3.2 Detection Functions

#### has_dependency_files(repo_analysis)
- **Purpose**: Detect presence of OSS dependency files
- **Checks**: go.mod, requirements.txt, package.json, pom.xml, setup.py, pyproject.toml
- **Returns**: Boolean

#### is_monorepo_structure(repo_analysis)
- **Purpose**: Detect monorepo structure
- **Checks**: Multiple project directories, shared dependency locations, hierarchical structure
- **Returns**: Boolean

#### has_runtime_evidence(repo_analysis)
- **Purpose**: Detect runtime configuration evidence
- **Checks**: Jenkins logs, build configurations, environment variables
- **Returns**: Boolean

#### is_minimal_content(repo_analysis)
- **Purpose**: Detect minimal repository content
- **Checks**: File count, file types, repository size
- **Returns**: Boolean

---

## 4. Minimal Repository Handling

### 4.1 Detection Criteria

A repository is classified as minimal when:
- No dependency files found (go.mod, requirements.txt, package.json, pom.xml, setup.py, pyproject.toml)
- Minimal file structure (typically only README.md)
- No source code files (.py, .go, .js, .java, etc.)
- No configuration files (Dockerfile, Makefile, Jenkinsfile, etc.)
- Total file count < 10 files
- Total repository size < 100KB

### 4.2 Compliance Reporting

#### Status Display
- **Primary Status**: "No OSS components detected"
- **Secondary Status**: "Minimal repository - no dependency files found"
- **Compliance Percentage**: N/A (not applicable) or "0% (0/0 components - no OSS components to assess)"

#### Contextual Information
- Repository classification explanation
- File structure summary
- Runtime evidence availability
- Recommendations for investigation

#### Evidence Presentation
- Display runtime evidence if available from Jenkins
- Show Jenkins build configurations
- Present environment variable usage
- Link to related repositories if detected

### 4.3 User Experience

#### Clear Status Messages
- Distinguish between "0% compliance" and "No OSS components detected"
- Provide explanation of repository classification
- Show context for why compliance cannot be assessed

#### Actionable Recommendations
- Suggest investigation of repository structure
- Recommend checking parent repositories
- Advise reviewing build process configuration
- Provide guidance on dependency management

#### Visual Indicators
- Different color coding for minimal repositories
- Special icon or badge for repository classification
- Clear separation from compliance issues

---

## 5. Runtime Evidence vs. Static File Analysis

### 5.1 Dual Analysis Approach

The system performs both static file analysis and runtime evidence detection:

#### Static File Analysis
- Scans dependency files (go.mod, requirements.txt, package.json, pom.xml)
- Analyzes configuration files (Dockerfile, Makefile, Jenkinsfile)
- Inspects source code for direct URL references
- Validates proxy configurations
- Enumerates OSS components

#### Runtime Evidence Analysis
- Analyzes Jenkins build logs for runtime configurations
- Detects environment variable usage
- Identifies build-time dependency injection
- Validates pipeline configurations
- Extracts runtime endpoint configurations

### 5.2 Discrepancy Handling

#### Scenario 1: Static Files Present, Runtime Evidence Missing
- **Classification**: Potential configuration issue
- **Action**: Flag for investigation
- **Recommendation**: Verify Jenkins configuration matches static files
- **Severity**: Medium

#### Scenario 2: Runtime Evidence Present, Static Files Missing
- **Classification**: Minimal repository with external dependencies
- **Action**: Investigate repository structure
- **Recommendation**: Check parent repositories or dependency sources
- **Severity**: Low

#### Scenario 3: Both Present
- **Classification**: Standard repository with runtime validation
- **Action**: Validate consistency between static and runtime configurations
- **Recommendation**: Ensure configurations are aligned
- **Severity**: Informational

#### Scenario 4: Both Missing
- **Classification**: Repository may not require OSS dependencies
- **Action**: Confirm repository purpose
- **Recommendation**: Verify if OSS dependencies are needed
- **Severity**: Informational

### 5.3 Evidence Integration

#### Merged Report Structure
```json
{
  "repository_classification": "MINIMAL",
  "static_analysis": {
    "components_found": 0,
    "dependency_files": [],
    "configuration_files": []
  },
  "runtime_analysis": {
    "components_detected": 15,
    "jenkins_evidence": true,
    "configurations_found": ["pip index-url", "environment variables"]
  },
  "compliance_assessment": {
    "status": "No OSS components detected in static files",
    "runtime_compliance": "Based on Jenkins evidence: 100% compliant",
    "recommendation": "Investigate repository structure and dependency management"
  }
}
```

---

## 6. Monorepo Support Considerations

### 6.1 Current Limitations

- **Single Repository Scanning**: Scans entire repository as single unit
- **Flat Dependency Analysis**: Doesn't account for project hierarchies
- **Shared Dependency Tracking**: Limited support for shared dependencies
- **Selective Scanning**: Cannot scan specific projects within monorepo

### 6.2 Planned Enhancements

#### Project Detection
- Analyze repository structure for project directories
- Identify project boundaries and shared dependencies
- Detect common monorepo patterns (projects/, packages/, services/)

#### Hierarchical Scanning
- Scan individual projects independently
- Aggregate results at repository level
- Provide project-specific compliance reports
- Enable repository-level compliance summary

#### Dependency Mapping
- Track shared dependencies across projects
- Identify dependency relationships
- Map dependency usage patterns
- Optimize scanning based on dependency graph

#### Selective Scanning
- Allow scanning specific projects within monorepo
- Support project-level scan triggers
- Enable incremental scanning for large monorepos
- Provide project selection UI

### 6.3 Implementation Strategy

#### Phase 1: Structure Detection
- Implement monorepo structure detection algorithm
- Identify project directories and shared dependencies
- Create repository structure analysis module

#### Phase 2: Hierarchical Scanning
- Implement project-level scanning
- Add repository-level aggregation
- Create hierarchical reporting system

#### Phase 3: Dependency Mapping
- Implement shared dependency tracking
- Add dependency relationship analysis
- Create dependency visualization

#### Phase 4: Selective Scanning
- Implement project selection UI
- Add incremental scanning support
- Create project-based scan triggers

---

## 7. Compliance Reporting Enhancements

### 7.1 Report Structure Updates

#### Classification Section
```json
{
  "repository_classification": {
    "type": "MINIMAL",
    "confidence": "high",
    "criteria": {
      "dependency_files_found": 0,
      "total_files": 1,
      "file_types": ["README.md"],
      "repository_size_kb": 2
    }
  }
}
```

#### Enhanced Compliance Status
```json
{
  "compliance_status": {
    "primary_status": "No OSS components detected",
    "secondary_status": "Minimal repository - no dependency files found",
    "compliance_percentage": "N/A",
    "assessment_basis": "Static file analysis",
    "runtime_evidence_available": true
  }
}
```

### 7.2 User Interface Updates

#### Repository Classification Badge
- Visual indicator of repository type
- Color-coded by classification
- Tooltip with classification details

#### Enhanced Status Messages
- Clear distinction between compliance issues and repository structure
- Contextual information for minimal repositories
- Actionable recommendations

#### Evidence Display
- Runtime evidence section when available
- Jenkins configuration details
- Environment variable usage

---

## 8. Implementation Requirements

### 8.1 New Components

#### Repository Classifier Module
- **File**: `repository_classifier.py`
- **Purpose**: Implement classification algorithm
- **Functions**: 
  - `classify_repository()`
  - `has_dependency_files()`
  - `is_monorepo_structure()`
  - `has_runtime_evidence()`
  - `is_minimal_content()`

#### Enhanced Reporting Module
- **File**: `enhanced_reporter.py`
- **Purpose**: Generate classification-aware reports
- **Functions**:
  - `generate_classification_report()`
  - `format_minimal_repository_status()`
  - `integrate_runtime_evidence()`

#### UI Updates
- **Files**: `templates/results.html`, `templates/reports.html`
- **Purpose**: Display classification information
- **Components**:
  - Classification badge
  - Enhanced status messages
  - Runtime evidence section

### 8.2 Database Schema Updates

#### Reports Table Enhancement
```sql
ALTER TABLE reports ADD COLUMN repository_classification VARCHAR(50);
ALTER TABLE reports ADD COLUMN classification_confidence VARCHAR(20);
ALTER TABLE reports ADD COLUMN runtime_evidence_available BOOLEAN DEFAULT FALSE;
```

### 8.3 API Updates

#### Scan Endpoint Enhancement
- Add classification parameter to response
- Include classification metadata
- Provide classification-specific recommendations

#### Report Endpoint Enhancement
- Add classification filter
- Include classification details in report view
- Support classification-based filtering

---

## 9. Testing Requirements

### 9.1 Unit Tests

#### Classification Algorithm Tests
- Test standard repository classification
- Test minimal repository classification
- Test runtime-only repository classification
- Test monorepo classification (future)

#### Detection Function Tests
- Test dependency file detection
- Test minimal content detection
- Test runtime evidence detection
- Test monorepo structure detection (future)

### 9.2 Integration Tests

#### End-to-End Classification Tests
- Test full scanning workflow with classification
- Test minimal repository handling
- Test runtime evidence integration
- Test report generation with classification

#### UI Tests
- Test classification badge display
- Test enhanced status messages
- Test runtime evidence section
- Test user experience for minimal repositories

### 9.3 Test Data

#### Standard Repository Test Data
- Repository with go.mod, requirements.txt, package.json
- Expected classification: STANDARD

#### Minimal Repository Test Data
- Repository with only README.md
- Expected classification: MINIMAL

#### Runtime-Only Repository Test Data
- Repository with no dependency files but Jenkins evidence
- Expected classification: RUNTIME_ONLY

#### Monorepo Test Data (Future)
- Repository with multiple projects
- Expected classification: MONOREPO

---

## 10. Success Criteria

### 10.1 Functional Requirements
- [ ] Repository classification algorithm implemented
- [ ] Minimal repository detection working correctly
- [ ] Runtime evidence integration functional
- [ ] Enhanced compliance reporting operational
- [ ] UI updates for classification display

### 10.2 Non-Functional Requirements
- [ ] Classification accuracy > 95%
- [ ] Performance impact < 5% overhead
- [ ] Backward compatibility maintained
- [ ] User experience improved for minimal repositories

### 10.3 Documentation Requirements
- [ ] HLD updated with classification system
- [ ] SDD updated with classification details
- [ ] User guide updated with classification information
- [ ] API documentation updated

---

## 11. Future Considerations

### 11.1 Advanced Classification
- Machine learning-based classification
- Automated repository pattern detection
- Dynamic classification rule updates

### 11.2 Enhanced Monorepo Support
- Dependency graph visualization
- Impact analysis for shared dependencies
- Cross-project compliance tracking

### 11.3 Integration Enhancements
- CI/CD platform integration for classification
- Automated classification-based routing
- Classification-based policy enforcement

---

## Appendix A: Classification Examples

### A.1 fusion-stage-backend Analysis

**Repository Content**:
- Files: README.md only
- Size: 22 bytes
- Dependency files: None
- Source code: None

**Classification**: MINIMAL

**Static Analysis**: 0 components detected

**Runtime Evidence**: Jenkins logs show pip index-url configuration for AWS CodeArtifact

**Compliance Status**: "No OSS components detected in static files. Runtime evidence suggests dependencies managed externally."

**Recommendation**: "Investigate repository structure - OSS dependencies may be in parent repository or managed through build process."

### A.2 fusion-stage Analysis

**Repository Content**:
- Files: Multiple source files, go.mod, requirements.txt, package.json
- Size: >1MB
- Dependency files: go.mod, requirements.txt, package.json
- Source code: Multiple Python and Go files

**Classification**: STANDARD

**Static Analysis**: 262 components detected

**Runtime Evidence**: Jenkins logs consistent with static configuration

**Compliance Status**: "70.61% compliance (185/262 components compliant)"

**Recommendation**: "Address non-compliant components by configuring approved Artifactory endpoints."

---

**Document Status**: Draft  
**Next Review**: 2026-06-30  
**Approved By**: Pending  
**Distribution**: Architecture Team, Development Team, QA Team