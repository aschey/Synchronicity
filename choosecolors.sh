#!/bin/bash
#while read p; do
#    r=${p:1:2}
#    g=${p:3:4}
#    b={p:5:6}
#    color='\e]4;'$i';rgb:'$r'/'$g'/'$b'\e\\\e[31m██ = '$p'\e[m\n'
    #color='\e]4;1;rgb:FF/00/00\e\\\e[31m██ = #FF0000\e[m\n'
#    printf $color
#done <colors.txt
printf '\e]4;1;rgb:AA/BB/CC\e\\\e[200m██ = #AABBCC\e[m\n'
printf '\e]4;1;rgb:99/00/00\e\\\e[29m██ = #990000\e[m\n'
