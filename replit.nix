{ pkgs }: {
  deps = [
    pkgs.python311
    pkgs.python311Packages.pip
    pkgs.python311Packages.setuptools
    pkgs.python311Packages.wheel
  ];

  # This ensures that pip installs your dependencies correctly
  env = {
    PYTHONNOUSERSITE = "true";
  };
}
