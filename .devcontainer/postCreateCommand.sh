# install zsh and oh-my-zsh
apt-get update
apt-get install -y zsh wget lsof
sh -c "$(wget -O- https://raw.githubusercontent.com/ohmyzsh/ohmyzsh/master/tools/install.sh)" "" --unattended

# install application
pip install -U pip
pip install -e .[testing]

# add alias autoformat for autoformatting, typical usage: autoformat **/*.py
pip install isort autoflake py-spy sqlparse jupyter jupyter_contrib_nbextensions
echo "alias autoformat='autoformatfun() { autoflake --in-place --exclude alembic --remove-all-unused-imports \$@ && isort \$@ && black \$@ };autoformatfun'" >> ~/.zshrc

# add alias jn for jupyter notebook
jupyter nbextension install https://github.com/drillan/jupyter-black/archive/master.zip --user
jupyter contrib nbextension install --user
jupyter nbextension enable jupyter-black-master/jupyter-black
jupyter nbextension enable execute_time/ExecuteTime

echo "alias jn='jupyter notebook --allow-root --ip 0.0.0.0 --no-browser'" >> ~/.zshrc