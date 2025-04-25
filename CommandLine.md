# 🖥️ Command Line Cheat Sheet

My guide to essential command line commands for navigating and managing the file system.

---

## 📁 Command Lines

These are the core commands used to explore and move through the file system:


| Command        | Description                                   |
|----------------|-----------------------------------------------|
| `pwd`          | Prints the working directory                  |
| `ls`           | Lists contents of the current directory       |
| `ls -l`        | Lists contents with more information          |
| `cd`           | Change directory                              |
| `cd ..`        | Go back one directory                         |
| `cd /`         | Go to root directory                          |
| `open`         | Open a folder or file                         |
| `mkdir`        | Create a new directory                        |
| `touch`        | Create a new file                             |
| `rm`           | Remove a file                                 |
| `rm -r`        | Remove a directory and its contents           |
| `cp`           | Copy a file or directory                      |
| `mv`           | Move or rename a file or directory            |


## 🛠️ Modifying Files & Directories


| Command                            | Description                                   |
|------------------------------------|-----------------------------------------------|
| `mkdir [dirname]`                  | Create directory                              |
| `touch [filename]`                 | Create file                                   |
| `rm [filename]`                    | Remove file                                   |
| `rm -i [filename]`                 | Remove file with confirmation                 |
| `rm -r [dirname]`                  | Remove directory                              |
| `rm -rf [dirname]`                 | Force remove directory and its contents       |
| `rm ./*`                           | Remove all files in current directory         |
| `cp [filename] [dirname]`          | Copy file to directory                        |
| `mv [filename] [dirname]`          | Move file to directory                        |
| `mv [filename] [filename]`         | Rename file                                   |
| `mv [filename] [filename] -v`      | Rename with verbose output                    |
| `cd test2 && mkdir test3`          | Chain multiple commands with `&&`             |

## 📄 The less Command

The less command is used to view the contents of a file. It is similar to the cat command, but it allows you to scroll up and down.
```
less [filename]
```

## 🗣️ The echo Command

The echo command is used to display messages or write to files.
```
echo "Hello World"
```

To write to a file:
```
echo "Hello World" > filename.txt
```

To append to a file:
```
echo "Another Line" >> filename.txt
```
## ✍️ The nano Command

The nano command is a text editor.
```
nano [filename]
```
Exit: Ctrl + X
Save: Press Y
Don’t save: Press N