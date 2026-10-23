"use strict";

// Publish only photos and public contact links supplied or confirmed by members.
// Photos should be local site assets; null keeps the initials placeholder.
const teamProfiles = {
  mrunal: {
    name: "Mrunal Vibhute",
    initials: "MV",
    role: "Project team",
    photo: "./assets/mrunal-vibhute.jpg",
    links: [
      {
        label: "LinkedIn",
        url: "https://www.linkedin.com/in/mrunal-vibhute-b6b392235/",
        qr: "./assets/qr/mrunal-linkedin.svg",
      },
    ],
  },
  shrimayee: {
    name: "Shrimayee Deshpande",
    initials: "SD",
    role: "Project team",
    photo: "./assets/shrimayee-deshpande.jpg",
    links: [
      {
        label: "LinkedIn",
        url: "https://www.linkedin.com/in/shrimayee/",
        qr: "./assets/qr/shrimayee-linkedin.svg",
      },
    ],
  },
  honey: {
    name: "Honey Reddy Daram",
    initials: "HD",
    role: "Project team",
    photo: "./assets/honey-reddy-daram.jpg",
    links: [
      {
        label: "Portfolio",
        url: "https://honeyreddydaram.github.io/Portfolio/",
      },
      {
        label: "LinkedIn",
        url: "https://www.linkedin.com/in/honeyreddydaram/",
        qr: "./assets/qr/honey-linkedin.svg",
      },
    ],
  },
  yasasvi: {
    name: "Yasasvi Kaipa",
    initials: "YK",
    role: "Project team",
    photo: "./assets/yasasvi-kaipa.jpg",
    links: [
      {
        label: "LinkedIn",
        url: "https://www.linkedin.com/in/yasasvikaipa/",
        qr: "./assets/qr/yasasvi-linkedin.svg",
      },
    ],
  },
  andrea: {
    name: "Dr. Andrea Ramirez-Salgado",
    initials: "AR",
    role: "Project advisor",
    photo: null,
    links: [],
  },
};
