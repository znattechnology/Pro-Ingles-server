# Changelog

## [Latest] - 2025-10-21

### Fixed
- Fixed test infrastructure issues and improved production robustness
- Resolved subscription plan creation conflicts using get_or_create pattern
- Fixed pagination issues in CMS tests with conditional response.data handling
- Updated subscription test URLs to match actual Django URL patterns
- Corrected subscription plan pricing to use real AOA (Kuanza) values
- Fixed check_subscription_limits to consistently return current_usage and limit fields

### Technical Improvements
- Replaced objects.create() with get_or_create() to prevent duplicate key constraints
- Enhanced endpoint robustness against missing FREE subscription plans
- Improved test data consistency with production pricing
- Standardized URL naming conventions across test files

### Test Coverage
- 292 tests now run with significantly reduced failures
- Eliminated NoReverseMatch errors in subscription tests
- Fixed calculation tests with realistic pricing scenarios
- Improved CMS pagination test reliability