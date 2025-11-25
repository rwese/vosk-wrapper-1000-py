class VoskWrapper1000 < Formula
  include Language::Python::Virtualenv

  desc "Modular speech recognition toolkit using Vosk with daemon and file transcription"
  homepage "https://github.com/rwese/vosk-wrapper-1000-py"
  url "https://github.com/rwese/vosk-wrapper-1000-py/archive/refs/tags/v0.1.0.tar.gz"
  sha256 "" # TODO: Update with actual SHA256 when releasing
  license "MIT"
  head "https://github.com/rwese/vosk-wrapper-1000-py.git", branch: "main"

  depends_on "python@3.12"
  depends_on "portaudio"
  depends_on "libsoxr"

  resource "vosk" do
    url "https://files.pythonhosted.org/packages/source/v/vosk/vosk-0.3.44.tar.gz"
    sha256 "TODO"
  end

  resource "sounddevice" do
    url "https://files.pythonhosted.org/packages/source/s/sounddevice/sounddevice-0.4.6.tar.gz"
    sha256 "TODO"
  end

  resource "numpy" do
    url "https://files.pythonhosted.org/packages/source/n/numpy/numpy-1.24.3.tar.gz"
    sha256 "TODO"
  end

  resource "scipy" do
    url "https://files.pythonhosted.org/packages/source/s/scipy/scipy-1.10.1.tar.gz"
    sha256 "TODO"
  end

  resource "requests" do
    url "https://files.pythonhosted.org/packages/source/r/requests/requests-2.31.0.tar.gz"
    sha256 "TODO"
  end

  resource "tqdm" do
    url "https://files.pythonhosted.org/packages/source/t/tqdm/tqdm-4.66.1.tar.gz"
    sha256 "TODO"
  end

  resource "noisereduce" do
    url "https://files.pythonhosted.org/packages/source/n/noisereduce/noisereduce-3.0.0.tar.gz"
    sha256 "TODO"
  end

  resource "soxr" do
    url "https://files.pythonhosted.org/packages/source/s/soxr/soxr-0.3.7.tar.gz"
    sha256 "TODO"
  end

  resource "PyYAML" do
    url "https://files.pythonhosted.org/packages/source/P/PyYAML/PyYAML-6.0.1.tar.gz"
    sha256 "TODO"
  end

  resource "textual" do
    url "https://files.pythonhosted.org/packages/source/t/textual/textual-0.47.0.tar.gz"
    sha256 "TODO"
  end

  resource "aiortc" do
    url "https://files.pythonhosted.org/packages/source/a/aiortc/aiortc-1.6.0.tar.gz"
    sha256 "TODO"
  end

  resource "av" do
    url "https://files.pythonhosted.org/packages/source/a/av/av-10.0.0.tar.gz"
    sha256 "TODO"
  end

  resource "aiohttp" do
    url "https://files.pythonhosted.org/packages/source/a/aiohttp/aiohttp-3.8.0.tar.gz"
    sha256 "TODO"
  end

  def install
    virtualenv_install_with_resources
  end

  def post_install
    # Create XDG directories
    (var/"lib/vosk-wrapper-1000/models").mkpath
    (etc/"vosk-wrapper-1000").mkpath
  end

  def caveats
    <<~EOS
      To start vosk-wrapper-1000 as a user service:
        brew services start vosk-wrapper-1000

      Or run manually:
        vosk-wrapper-1000 daemon

      Download a Vosk model:
        vosk-download-model-1000 vosk-model-small-en-us-0.15

      Models are stored in:
        #{HOMEBREW_PREFIX}/var/lib/vosk-wrapper-1000/models

      Configuration file location:
        #{ENV["HOME"]}/.config/vosk-wrapper-1000/config.yaml

      For more information:
        https://github.com/rwese/vosk-wrapper-1000-py
    EOS
  end

  service do
    run [opt_bin/"vosk-wrapper-1000", "daemon", "--name", "default", "--foreground"]
    keep_alive true
    working_dir var
    log_path var/"log/vosk-wrapper-1000.log"
    error_log_path var/"log/vosk-wrapper-1000-error.log"
    environment_variables PATH: std_service_path_env
  end

  test do
    # Test that the CLI is available
    assert_match "vosk-wrapper-1000", shell_output("#{bin}/vosk-wrapper-1000 --help")
    assert_match "vosk-download-model-1000", shell_output("#{bin}/vosk-download-model-1000 --help")
    assert_match "vosk-transcribe-file", shell_output("#{bin}/vosk-transcribe-file --help")
    assert_match "vosk-settings-tui", shell_output("#{bin}/vosk-settings-tui --help")
  end
end
