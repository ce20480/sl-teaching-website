# Contributing to the ASL Teaching Website

This guide explains how to contribute to our project, including code contributions and data contributions for model training.

## Code Contribution

### Setting Up the Development Environment

Follow the [Setup Guide](setup.md) to get your development environment ready.

### Contribution Workflow

1. **Fork the Repository**

   - Fork the repository on GitHub
   - Clone your fork locally: `git clone https://github.com/yourusername/asl-teaching-website.git`

2. **Create a Branch**

   - Create a feature branch: `git checkout -b feature/your-feature-name`

3. **Make Changes**

   - Write your code
   - Follow the coding standards and conventions
   - Add tests if applicable

4. **Test Your Changes**

   - Run the existing tests: `npm test` (frontend) or `pytest` (backend)
   - Ensure your changes don't break existing functionality

5. **Commit Your Changes**

   - Use clear and descriptive commit messages
   - Reference issue numbers if applicable: `fix: Resolve hand detection issue (#42)`

6. **Submit a Pull Request**
   - Push your changes to your fork: `git push origin feature/your-feature-name`
   - Create a pull request from your fork to the main repository
   - Describe your changes in detail

### Code Standards

- **Frontend**: Follow ESLint and Prettier configurations
- **Backend**: Follow PEP 8 style guide
- **Documentation**: Update documentation for any new features or changes

## Data Contribution

Our project relies on high-quality training data to improve the sign language detection model. You can contribute data through:

### 1. Using the Contribute Feature

The application has a built-in contribution feature where you can submit labeled hand landmarks:

```typescript
// Contribute data through the API
contributeData(landmarks, label);
```

### 2. Submitting Labeled Images

For bulk data contributions:

1. Organize images in folders by ASL letter
2. Ensure images are clear and focused on the hand
3. Submit a pull request with your data to the `data/raw` directory

### 3. Improving Existing Data

Help improve our existing dataset by:

- Cleaning up mislabeled samples
- Enhancing quality through normalization
- Adding metadata for better organization

## Package Contribution

To contribute to the sl-detection package:

1. Fork the [sl-detection repository](https://github.com/ce20480/SignLanguageDetection)
2. Make your changes
3. Update version numbers in `setup.py` and `sl_detection/__init__.py`
4. Submit a pull request

If you're a maintainer on PyPI:

```bash
pip install build twine
rm -rf dist/
python -m build
twine upload dist/*
```

## Documentation Contribution

We value documentation improvements:

1. Fix typos or clarify existing documentation
2. Add examples for complex features
3. Create tutorials for new users
4. Update API documentation when endpoints change

## Questions or Suggestions?

If you have questions or suggestions, please:

- Open an issue on GitHub
- Reach out to the maintainers
- Join our community discussions

Thank you for contributing to making sign language more accessible!
