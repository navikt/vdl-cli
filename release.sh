#!/bin/bash
set -e

git switch main
git pull
git push

uncommitted_files=$(git diff-index --quiet HEAD -- || echo "untracked")

continue="y"
if [ $uncommitted_files ]; then
    git status
    echo "There are uncommitted files. Do you want to continue? (Y/n)"
    read continue
    echo ""
    continue=${continue:-y}
fi

if [ "$continue" != "y" ]; then
    exit 0
fi

version=$(./.venv/bin/python -m setup --version)
major_minor=$(echo $version | cut -d. -f1,2)

echo "Release version $version? (Y/n)"
read continue
continue=${continue:-y}

if [ "$continue" != "y" ]; then
    exit 0
fi

git tag "v$version"
git push origin "v$version"
git tag -f "v$major_minor"
git push -f origin "v$major_minor"
gh release create "v$version" --generate-notes
